from __future__ import annotations

import argparse
import re
from typing import Iterable

import requests
from bs4 import BeautifulSoup
from langchain_core.documents import Document
from langchain_pinecone import PineconeEmbeddings, PineconeVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import get_settings


FAQ_URL = "https://www.tsa.gov/travel/frequently-asked-questions"
FAQ_NAMESPACE = "tsa-faq"


def fetch_static_html(url: str) -> str:
    response = requests.get(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36"
            )
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.text


def fetch_rendered_html(url: str) -> str:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("Playwright is not installed.") from exc

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="networkidle", timeout=60_000)
        html = page.content()
        browser.close()
        return html


def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def soup_to_documents(html: str, source_url: str) -> list[Document]:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "nav", "footer", "header"]):
        tag.decompose()

    main = soup.find("main") or soup.find(id=re.compile("faq|content", re.I)) or soup.body
    if main is None:
        return []

    docs: list[Document] = []
    headings = main.find_all(["h1", "h2", "h3", "h4"])

    for heading in headings:
        title = clean_text(heading.get_text(" "))
        if not title or len(title) < 4:
            continue

        parts = []
        for sibling in heading.find_next_siblings():
            if sibling.name in ["h1", "h2", "h3", "h4"]:
                break
            text = clean_text(sibling.get_text(" "))
            if text:
                parts.append(text)

        body = clean_text(" ".join(parts))
        if body and len(body) > 40:
            docs.append(
                Document(
                    page_content=f"Question or section: {title}\nAnswer: {body}",
                    metadata={"source": source_url, "title": title},
                )
            )

    if docs:
        return deduplicate_documents(docs)

    fallback_text = clean_text(main.get_text(" "))
    if not fallback_text:
        return []
    return [
        Document(
            page_content=fallback_text,
            metadata={"source": source_url, "title": "Allegiant Air FAQs"},
        )
    ]


def deduplicate_documents(documents: Iterable[Document]) -> list[Document]:
    seen = set()
    unique = []
    for document in documents:
        key = document.page_content.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(document)
    return unique


def load_faq_documents(url: str) -> list[Document]:
    documents: list[Document] = []
    try:
        html = fetch_static_html(url)
        documents = soup_to_documents(html, url)
    except requests.HTTPError as exc:
        print(f"Static fetch skipped: {exc}")

    # The FAQ page may hydrate content with JavaScript. If the static response is
    # blocked or too thin, retry with a rendered browser page.
    if len(documents) < 5:
        try:
            rendered_html = fetch_rendered_html(url)
            rendered_documents = soup_to_documents(rendered_html, url)
            if len(rendered_documents) > len(documents):
                documents = rendered_documents
        except Exception as exc:
            print(f"Rendered fetch skipped: {exc}")

    if not documents:
        raise RuntimeError("No FAQ content could be extracted.")

    return documents


def ingest(url: str = FAQ_URL) -> int:
    settings = get_settings()
    documents = load_faq_documents(url)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=900,
        chunk_overlap=150,
        separators=["\n\n", "\n", ". ", "? ", "! ", " ", ""],
    )
    chunks = splitter.split_documents(documents)

    embeddings = PineconeEmbeddings(
        pinecone_api_key=settings.pinecone_api_key,
        model=settings.pinecone_embedding_model,
        dimension=settings.pinecone_embedding_dimension,
    )
    PineconeVectorStore.from_documents(
        documents=chunks,
        embedding=embeddings,
        index_name=settings.pinecone_index_name,
        namespace=FAQ_NAMESPACE,
    )

    return len(chunks)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest Allegiant FAQ content to Pinecone.")
    parser.add_argument("--url", default=FAQ_URL)
    args = parser.parse_args()

    count = ingest(args.url)
    print(f"Ingested {count} chunks into Pinecone.")
