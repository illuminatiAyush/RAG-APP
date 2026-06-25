import asyncio
from pathlib import Path
import time

import streamlit as st
import inngest
from dotenv import load_dotenv
import os
import requests

load_dotenv()

st.set_page_config(page_title="RAG Ingest PDF", layout="centered")


@st.cache_resource
def get_inngest_client() -> inngest.Inngest:
    return inngest.Inngest(app_id="rag_app", is_production=False)


def save_uploaded_pdf(file) -> Path:
    uploads_dir = Path("uploads")
    uploads_dir.mkdir(parents=True, exist_ok=True)
    file_path = uploads_dir / file.name
    file_bytes = file.getbuffer()
    file_path.write_bytes(file_bytes)
    return file_path


async def send_rag_ingest_event(pdf_path: Path) -> None:
    client = get_inngest_client()
    await client.send(
        inngest.Event(
            name="rag/ingest_pdf",
            data={
                "pdf_path": str(pdf_path.resolve()),
                "source_id": pdf_path.name,
            },
        )
    )


# Header Section
st.markdown("""
<div style="text-align: center; padding: 20px 0 10px 0;">
    <h1 style="color: #eab308; margin-bottom: 5px;">RAG Production Engine</h1>
    <p style="font-size: 1.1em; color: #a1a1aa; max-width: 700px; margin: 0 auto; line-height: 1.6;">
        An event-driven <b>Retrieval-Augmented Generation (RAG)</b> application powered by <b>Inngest</b>, 
        <b>Qdrant Vector Database</b>, and <b>Groq (Llama-3)</b>.
    </p>
</div>
""", unsafe_allow_html=True)

# Project Description Details
with st.expander("How This System Works", expanded=False):
    st.markdown("""
    This application utilizes an asynchronous, event-driven architecture to ingest PDFs and run semantic queries:
    
    1. **PDF Ingestion:** Uploaded files are chunked into semantic fragments using `llama-index` sentence splitters.
    2. **Local Vector Embeddings:** Chunks are vectorized locally on-device using `fastembed` (`BAAI/bge-small-en-v1.5` model) to protect data privacy and reduce network latency.
    3. **Vector Storage:** Embeddings and document metadata are stored in a local **Qdrant Vector Database**.
    4. **Event Orchestration:** Inngest queues and manages the asynchronous execution steps, ensuring failure recovery and step re-runs.
    5. **Generative QA:** Queries retrieve matching context from Qdrant and pass it to **Groq's Llama-3** API to synthesize a factual, context-grounded answer.
    """)

st.divider()

st.markdown('<h3 style="color: #eab308; margin-bottom: 10px;">Ingest PDF Documents</h3>', unsafe_allow_html=True)
uploaded = st.file_uploader("Upload a PDF to parse and embed into Qdrant", type=["pdf"], accept_multiple_files=False)

if uploaded is not None:
    with st.spinner("Processing PDF, generating embeddings, and storing in Qdrant..."):
        path = save_uploaded_pdf(uploaded)
        # Kick off the event and block until the send completes
        asyncio.run(send_rag_ingest_event(path))
        # Small pause for user feedback continuity
        time.sleep(0.3)
    st.success(f"Successfully triggered ingestion for: {path.name}")
    st.caption("The document is now being processed asynchronously by Inngest.")

st.divider()
st.markdown('<h3 style="color: #eab308; margin-bottom: 10px;">Query Knowledge Base</h3>', unsafe_allow_html=True)


async def send_rag_query_event(question: str, top_k: int) -> None:
    client = get_inngest_client()
    result = await client.send(
        inngest.Event(
            name="rag/query_pdf_ai",
            data={
                "question": question,
                "top_k": top_k,
            },
        )
    )

    return result[0]


def _inngest_api_base() -> str:
    # Local dev server default; configurable via env
    return os.getenv("INNGEST_API_BASE", "http://127.0.0.1:8288/v1")


def fetch_runs(event_id: str) -> list[dict]:
    url = f"{_inngest_api_base()}/events/{event_id}/runs"
    resp = requests.get(url)
    resp.raise_for_status()
    data = resp.json()
    return data.get("data", [])


def wait_for_run_output(event_id: str, timeout_s: float = 120.0, poll_interval_s: float = 0.5) -> dict:
    start = time.time()
    last_status = None
    while True:
        runs = fetch_runs(event_id)
        if runs:
            run = runs[0]
            status = run.get("status")
            last_status = status or last_status
            if status in ("Completed", "Succeeded", "Success", "Finished"):
                return run.get("output") or {}
            if status in ("Failed", "Cancelled"):
                raise RuntimeError(f"Function run {status}")
        if time.time() - start > timeout_s:
            raise TimeoutError(f"Timed out waiting for run output (last status: {last_status})")
        time.sleep(poll_interval_s)


with st.form("rag_query_form"):
    question = st.text_input("Ask a question about your ingested documents")
    top_k = st.number_input("Context matches to retrieve (top_k)", min_value=1, max_value=20, value=5, step=1)
    submitted = st.form_submit_button("Search & Synthesize")

    if submitted and question.strip():
        with st.spinner("Retrieving contexts and generating answer..."):
            # Fire-and-forget event to Inngest for observability/workflow
            event_id = asyncio.run(send_rag_query_event(question.strip(), int(top_k)))
            # Poll the local Inngest API for the run's output
            output = wait_for_run_output(event_id)
            answer = output.get("answer", "")
            sources = output.get("sources", [])

        st.markdown('<h4 style="color: #eab308; margin-top: 20px; margin-bottom: 5px;">Answer</h4>', unsafe_allow_html=True)
        st.write(answer or "(No answer returned)")
        if sources:
            st.markdown("---")
            st.markdown("**Cited Sources:**")
            for s in sources:
                st.markdown(f"- `{Path(s).name}`")

# Footer Section
st.markdown("""
<div style="text-align: center; margin-top: 50px; padding: 20px 0; border-top: 1px solid #18181b; color: #71717a; font-size: 0.85em;">
    <p>Powered by Inngest, Qdrant, FastEmbed, and Groq Cloud API.</p>
</div>
""", unsafe_allow_html=True)

