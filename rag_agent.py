from __future__ import annotations

from typing import Literal, TypedDict

from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_pinecone import PineconeEmbeddings, PineconeVectorStore
from langgraph.graph import END, StateGraph

from config import get_settings


FAQ_NAMESPACE = "tsa-faq"


class AgentState(TypedDict, total=False):
    question: str
    documents: list[Document]
    context: str
    relevance: str
    answer: str
    grounded: str
    relevance_raw: str
    grounded_raw: str
    final_answer: str
    sources: list[dict[str, str]]


def _format_context(documents: list[Document]) -> str:
    formatted = []
    for index, doc in enumerate(documents, start=1):
        title = doc.metadata.get("title", "Travel FAQ")
        formatted.append(f"[{index}] {title}\n{doc.page_content}")
    return "\n\n".join(formatted)


def _source_payload(documents: list[Document]) -> list[dict[str, str]]:
    sources = []
    for index, doc in enumerate(documents, start=1):
        sources.append(
            {
                "id": str(index),
                "title": doc.metadata.get("title", "Travel FAQ"),
                "source": doc.metadata.get("source", ""),
                "snippet": doc.page_content[:700],
            }
        )
    return sources


def _is_yes(text: str) -> bool:
    normalized = text.strip().lower()
    if normalized.startswith("yes"):
        return True
    if "\nyes" in normalized or " yes" in normalized:
        return True
    support_phrases = [
        "can answer",
        "is allowed",
        "it's allowed",
        "it is allowed",
        "context contains",
        "context provides",
        "fully supported",
        "supported by the faq context",
        "supported by the context",
    ]
    return any(phrase in normalized for phrase in support_phrases)


def build_agent():
    settings = get_settings()
    answer_llm = ChatOpenAI(
        api_key=settings.nebius_api_key,
        base_url=settings.nebius_base_url,
        model=settings.deepseek_model,
        temperature=0,
    )
    judge_llm = ChatOpenAI(
        api_key=settings.nebius_api_key,
        base_url=settings.nebius_base_url,
        model=settings.qwen_model,
        temperature=0,
        max_tokens=128,
    )
    embeddings = PineconeEmbeddings(
        pinecone_api_key=settings.pinecone_api_key,
        model=settings.pinecone_embedding_model,
        dimension=settings.pinecone_embedding_dimension,
    )
    vector_store = PineconeVectorStore(
        index_name=settings.pinecone_index_name,
        embedding=embeddings,
        namespace=FAQ_NAMESPACE,
    )
    retriever = vector_store.as_retriever(search_kwargs={"k": 5})

    relevance_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You grade whether the retrieved FAQ context can answer the user's "
                "question. Do not think step by step. Reply with exactly 'yes' or 'no'.",
            ),
            ("human", "/no_think\nQuestion: {question}\n\nContext:\n{context}"),
        ]
    )

    answer_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a travel customer support assistant answering TSA FAQ "
                "questions. Answer only from the provided FAQ context. If the context does not contain the "
                "answer, say you could not find that in the FAQ. Include citation "
                "markers like [1] for every factual claim.",
            ),
            ("human", "Question: {question}\n\nFAQ context:\n{context}"),
        ]
    )

    verifier_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Check whether the answer is fully supported by the FAQ context. "
                "Do not think step by step. Reply with exactly 'yes' or 'no'.",
            ),
            ("human", "/no_think\nContext:\n{context}\n\nAnswer:\n{answer}"),
        ]
    )

    def retrieve(state: AgentState) -> AgentState:
        documents = retriever.invoke(state["question"])
        return {
            **state,
            "documents": documents,
            "context": _format_context(documents),
            "sources": _source_payload(documents),
        }

    def grade_relevance(state: AgentState) -> AgentState:
        response = judge_llm.invoke(
            relevance_prompt.format_messages(
                question=state["question"], context=state["context"]
            )
        )
        raw = response.content.strip()
        return {
            **state,
            "relevance_raw": raw,
            "relevance": "yes" if _is_yes(raw) else "no",
        }

    def generate_answer(state: AgentState) -> AgentState:
        response = answer_llm.invoke(
            answer_prompt.format_messages(
                question=state["question"], context=state["context"]
            )
        )
        return {**state, "answer": response.content.strip()}

    def verify_answer(state: AgentState) -> AgentState:
        response = judge_llm.invoke(
            verifier_prompt.format_messages(
                context=state["context"], answer=state["answer"]
            )
        )
        raw = response.content.strip()
        return {
            **state,
            "grounded_raw": raw,
            "grounded": "yes" if _is_yes(raw) else "no",
        }

    def no_answer(state: AgentState) -> AgentState:
        return {
            **state,
            "final_answer": (
                "I could not find enough support for that answer in the TSA FAQ. "
                "Please check the TSA site directly or contact TSA customer support."
            ),
        }

    def finalize(state: AgentState) -> AgentState:
        return {**state, "final_answer": state["answer"]}

    def route_after_relevance(state: AgentState) -> Literal["generate_answer", "no_answer"]:
        return "generate_answer" if state["relevance"] == "yes" else "no_answer"

    def route_after_verification(state: AgentState) -> Literal["finalize", "no_answer"]:
        return "finalize" if state["grounded"] == "yes" else "no_answer"

    graph = StateGraph(AgentState)
    graph.add_node("retrieve", retrieve)
    graph.add_node("grade_relevance", grade_relevance)
    graph.add_node("generate_answer", generate_answer)
    graph.add_node("verify_answer", verify_answer)
    graph.add_node("no_answer", no_answer)
    graph.add_node("finalize", finalize)

    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "grade_relevance")
    graph.add_conditional_edges("grade_relevance", route_after_relevance)
    graph.add_edge("generate_answer", "verify_answer")
    graph.add_conditional_edges("verify_answer", route_after_verification)
    graph.add_edge("no_answer", END)
    graph.add_edge("finalize", END)

    return graph.compile()


def answer_question(question: str) -> AgentState:
    agent = build_agent()
    return agent.invoke({"question": question})
