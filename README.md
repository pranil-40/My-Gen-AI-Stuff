# Agentic RAG Customer Support Demo

This project answers TSA travel FAQ questions with a LangGraph agent backed by
LangChain, Nebius-hosted chat models, Pinecone embeddings, and a Pinecone vector
database.

## Files

- `ingest_faq.py` parses `https://www.tsa.gov/travel/frequently-asked-questions`, chunks the cleaned
  FAQ content, embeds it, and stores it in Pinecone.
- `rag_agent.py` contains the LangGraph RAG workflow separate from the UI.
- `customer support.py` is the Streamlit web interface.
- `config.py` loads shared settings from `.env`.

## Nebius API Key

1. Sign in to your Nebius account.
2. Open the API keys section for AI Studio or Token Factory.
3. Create a new secret key.
4. Put it in `.env` as `NEBIUS_API_KEY=your-key-here`.

The demo uses DeepSeek for answer generation, Qwen for compact relevance and
grounding checks, and Pinecone `llama-text-embed-v2` embeddings to match the
`genaidemo` index dimension.

## Environment

Your `.env` should contain:

```bash
PINECONE_API_KEY=your-pinecone-key
PINECONE_INDEX_NAME=genaidemo
PINECONE_EMBEDDING_MODEL=llama-text-embed-v2
PINECONE_EMBEDDING_DIMENSION=1024
NEBIUS_API_KEY=your-nebius-key
NEBIUS_BASE_URL=https://api.tokenfactory.nebius.com/v1/
DEEPSEEK_MODEL=deepseek-ai/DeepSeek-V3.2-fast
QWEN_MODEL=Qwen/Qwen3-32B
```

## Run

Install dependencies:

```bash
uv sync
```

If the FAQ page needs JavaScript rendering on your machine, install the
Playwright browser once:

```bash
uv run playwright install chromium
```

Ingest FAQ data:

```bash
uv run python ingest_faq.py
```

Start the demo app:

```bash
uv run streamlit run "customer support.py"
```

## Agent Flow

The UI calls `answer_question()` from `rag_agent.py`. The graph retrieves FAQ
chunks, grades whether the context can answer the question, generates a grounded
answer with citations, verifies the answer against the context, and falls back to
an insufficient-context response when support is weak.
