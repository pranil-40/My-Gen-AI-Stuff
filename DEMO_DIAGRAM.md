# Agentic RAG Demo Diagram

Use this diagram while demonstrating both the code and the running Streamlit app.

```mermaid
flowchart LR
    subgraph Code["Code Layer"]
        A["ingest_faq.py<br/>Fetch TSA FAQ page"]
        B["Clean + parse HTML<br/>BeautifulSoup"]
        C["Chunk documents<br/>RecursiveCharacterTextSplitter"]
        D["Embed chunks<br/>Pinecone llama-text-embed-v2<br/>1024 dimensions"]
        E["rag_agent.py<br/>LangGraph workflow"]
        F["customer support.py<br/>Streamlit chat UI"]
        G["config.py + .env<br/>Keys, model names, index settings"]
    end

    subgraph Data["Vector Database"]
        P["Pinecone index: genaidemo<br/>Namespace: tsa-faq<br/>FAQ chunks + vectors"]
    end

    subgraph Runtime["Website / User Flow"]
        U["User asks question<br/>in Streamlit"]
        R["Retrieve relevant FAQ chunks"]
        J1["Qwen relevance check<br/>Can context answer?"]
        L["DeepSeek answer generation<br/>Cited, grounded answer"]
        J2["Qwen grounding check<br/>Is answer supported?"]
        O["Answer + source snippets<br/>shown in website"]
        X["Fallback response<br/>when support is weak"]
    end

    G --> A
    A --> B --> C --> D --> P
    G --> E
    F --> E
    U --> F --> E
    E --> R --> P
    P --> R --> J1
    J1 -- yes --> L --> J2
    J2 -- yes --> O
    J1 -- no --> X
    J2 -- no --> X
    X --> O
```

## Demo Talk Track

Start with the ingestion side:

1. Open `ingest_faq.py`.
2. Explain that this is the offline data-loading step.
3. It fetches the TSA FAQ page, cleans the HTML, extracts FAQ sections, chunks them, embeds them with Pinecone `llama-text-embed-v2`, and writes them into the `genaidemo` Pinecone index under the `tsa-faq` namespace.

Key line:

> "The website does not scrape the FAQ live. We first build a searchable knowledge base in Pinecone."

Then show the configuration:

1. Open `.env`.
2. Point out Pinecone settings, Nebius settings, DeepSeek model, and Qwen model.
3. Mention that Pinecone handles embeddings because the index is already configured for `llama-text-embed-v2` with 1024 dimensions.

Key line:

> "The embedding model must match the Pinecone index dimension, so ingestion and retrieval use the same Pinecone embedding model."

Then show the agent:

1. Open `rag_agent.py`.
2. Walk through the graph:
   - retrieve
   - grade relevance
   - generate answer
   - verify grounding
   - return final answer or fallback

Key line:

> "This is agentic RAG because the system does more than retrieve and answer. It evaluates whether the context is relevant, generates a grounded response, and verifies the answer before showing it."

Then show the website:

1. Open `customer support.py`.
2. Explain that the UI is intentionally thin.
3. It accepts a user question, calls `answer_question()` from `rag_agent.py`, and displays the answer plus source snippets.

Key line:

> "The UI and agent are separated, so this Streamlit frontend could be replaced by another website without rewriting the RAG logic."

## Video Demo Sequence

1. Show `ingest_faq.py`.
2. Run:

```powershell
uv run python ingest_faq.py
```

3. Show Pinecone index `genaidemo`, namespace `tsa-faq`, and vector count.
4. Show `rag_agent.py` and explain the LangGraph nodes.
5. Run the app:

```powershell
uv run streamlit run "customer support.py"
```

6. Ask a supported question:

```text
Can I carry liquid soap in my cabin bag?
```

7. Expand sources and show the cited context.
8. Ask an unsupported question:

```text
What should I do if my checked bag is missing?
```

9. Explain the fallback:

> "The TSA FAQ does not contain a strong answer for airline baggage-claim issues, so the agent refuses to hallucinate."

## Short Version

```mermaid
sequenceDiagram
    participant User
    participant UI as Streamlit UI
    participant Agent as LangGraph Agent
    participant Pinecone
    participant Qwen as Qwen Judge
    participant DeepSeek

    User->>UI: Ask travel FAQ question
    UI->>Agent: answer_question(question)
    Agent->>Pinecone: Retrieve relevant FAQ chunks
    Pinecone-->>Agent: Top matching chunks
    Agent->>Qwen: Is context relevant?
    alt Relevant
        Agent->>DeepSeek: Generate cited answer from context
        DeepSeek-->>Agent: Draft answer
        Agent->>Qwen: Is answer grounded?
        alt Grounded
            Agent-->>UI: Final answer + sources
        else Not grounded
            Agent-->>UI: Fallback response
        end
    else Not relevant
        Agent-->>UI: Fallback response
    end
    UI-->>User: Display answer and source snippets
```
