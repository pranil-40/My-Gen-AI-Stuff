import streamlit as st

from rag_agent import answer_question


st.set_page_config(page_title="Travel FAQ Support", page_icon="?", layout="wide")

st.title("Travel FAQ Support")
st.caption("Agentic RAG demo using LangChain, Pinecone, LangGraph, and Nebius.")

with st.sidebar:
    st.header("Status")
    st.write("Answers are grounded in the Pinecone FAQ index.")
    st.write("Run ingestion before asking questions.")
    st.code("uv run python ingest_faq.py", language="bash")

question = st.chat_input("Ask a question about TSA travel FAQs")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("sources"):
            with st.expander("Sources"):
                for source in message["sources"]:
                    st.markdown(f"**[{source['id']}] {source['title']}**")
                    if source["source"]:
                        st.markdown(source["source"])
                    st.caption(source["snippet"])

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Retrieving, checking, and answering..."):
            try:
                result = answer_question(question)
                answer = result.get("final_answer", "I could not produce an answer.")
                sources = result.get("sources", [])
                debug = {
                    "retrieved_chunks": len(result.get("documents", [])),
                    "relevance": result.get("relevance", "unknown"),
                    "grounded": result.get("grounded", "unknown"),
                }
            except Exception as exc:
                answer = f"Something went wrong: {exc}"
                sources = []
                debug = {}

        st.markdown(answer)
        if debug:
            st.caption(
                " | ".join(f"{key}: {value}" for key, value in debug.items())
            )
        if sources:
            with st.expander("Sources"):
                for source in sources:
                    st.markdown(f"**[{source['id']}] {source['title']}**")
                    if source["source"]:
                        st.markdown(source["source"])
                    st.caption(source["snippet"])

    st.session_state.messages.append(
        {"role": "assistant", "content": answer, "sources": sources}
    )
