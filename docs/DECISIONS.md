# Architecture Decision Records (ADR)

This document contains the Architecture Decision Records (ADR) detailing the design, trade-offs, and technology evaluations of the RAG Production Engine.

---

## ADR-001: Vector Storage Selection (Qdrant)

### Context & Problem
We required a vector database to store document chunk text payloads and their associated numerical embeddings to perform fast similarity searches.

### Alternatives Evaluated
*   **Pinecone:** Closed-source, cloud-managed only. Excellent developer experience but expensive at scale and presents privacy compliance hurdles since raw customer text payloads leave the local infrastructure.
*   **Weaviate:** Open-source, robust, written in Go. Very rich feature set but has higher baseline memory and CPU footprints.
*   **Qdrant:** Open-source, written in Rust. Extremely memory-efficient, supports native local Docker runs, and provides a clean, modern Python client.

### Decision
We selected **Qdrant** because it is open-source, highly performant on standard CPU hardware, allows for zero-cost local prototyping via Docker, and supports strict payload filtering to isolate tenant metrics.

### Consequences & Tradeoffs
We must manage Qdrant’s stateful container backup (via Snapshots) and ensure adequate storage volumes.

---

## ADR-002: Workflow Orchestration Layer (Inngest)

### Context & Problem
PDF parsing, chunking, and embedding generation are heavy, long-running, CPU-bound operations. Doing these synchronously within FastAPI HTTP endpoints causes thread starvation and timeouts. We needed an asynchronous worker/queue system.

### Alternatives Evaluated
*   **Celery:** The standard Python async task queue. Requires running a separate broker (Redis or RabbitMQ) and separate background worker processes. Managing Celery, state synchronization, and retry configs adds heavy maintenance overhead.
*   **Temporal:** Extremely powerful orchestrator. However, running Temporal requires a separate database cluster and complex worker setup, which is overengineered for our current load.
*   **Inngest:** Orchestration server that coordinates steps by triggering them via HTTP callbacks (`/api/inngest`). 

### Decision
We selected **Inngest** because it removes the need to maintain persistent task broker hardware. It provides step-level idempotency, retries with exponential backoff, rate limiting, and throttling natively through a single API server integration.

### Consequences & Tradeoffs
FastAPI must expose a public HTTP endpoint (`/api/inngest`) for Inngest to trigger. In production, this route must be protected with signature verification keys.

---

## ADR-003: Local Text Embedding Model (FastEmbed)

### Context & Problem
We needed an embedding model to convert text chunks into numerical vectors.

### Alternatives Evaluated
*   **OpenAI Embeddings API (`text-embedding-3-small`):** High quality, but introduces per-token API costs and adds external network calls, which can fail.
*   **FastEmbed (Local `BAAI/bge-small-en-v1.5`):** Runs locally on CPU using optimized ONNX runtimes.

### Decision
We selected **FastEmbed** to keep the core retrieval system private and zero-cost. The `bge-small-en-v1.5` model (384 dimensions) runs locally, is fast, and offers high semantic accuracy.

### Consequences & Tradeoffs
Running embeddings locally consumes server CPU cycles. Under high ingestion loads, CPU usage will spike.

---

## ADR-004: Package Directory Layout Restructure

### Context & Problem
The initial workspace had all source files (`main.py`, `data_loader.py`, etc.) directly at the root. This cluttered the root workspace, made packaging difficult, and caused local module resolution conflicts.

### Decision
We restructured the files into a clean Python package inside `app/` containing an `__init__.py`. Documentation was structured inside `docs/`.

### Consequences & Tradeoffs
Running commands must now reference the `app` package context (e.g., `uvicorn app.main:app` instead of `uvicorn main:app`).
