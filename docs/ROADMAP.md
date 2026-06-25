# Application Development Roadmap

This document outlines the evolutionary roadmap of the RAG Production Engine, transitioning from MVP to an enterprise-scale multi-tenant system.

---

## Phase 1: Minimum Viable Product (Current State)

*   [x] **Local Vector Embeddings:** Integrated FastEmbed ONNX local CPU execution for privacy and cost savings.
*   [x] **Vector Storage:** Persisted schemas in Qdrant collections.
*   [x] **FastAPI & Inngest Orchestration:** Asynchronous pipeline running step functions.
*   [x] **Rate Limiting & Throttling:** Implemented ingestion controls to prevent CPU exhaustion.
*   [x] **User Interface:** Interactive Streamlit frontend.

---

## Phase 2: Production Hardening (Next Steps)

*   [ ] **GPU Embedding Worksheets:** Move local `fastembed` tasks from CPU threads to dedicated GPU instances (using Hugging Face's TEI or local NVIDIA-based workers) to handle larger documents.
*   [ ] **LLM Failure Recovery Retries:** Implement custom retry policies with exponential backoff on `ctx.step.ai.infer` tasks to prevent API rate-limit dropouts.
*   [ ] **Database Connection Pooling:** Set up persistent gRPC/HTTP connection pools for the Qdrant Client to avoid connection establishment latency.
*   [ ] **Structured Logging & APM Integration:** Export structured performance metrics (e.g., PDF parse times, upsert times) to tools like Prometheus and Datadog via OpenTelemetry.

---

## Phase 3: Enterprise Features

*   [ ] **User Authentication & RBAC (Role-Based Access Control):** Integrate Auth0 or Clerk. Ensure users can only search documents they have uploaded or have permission to access.
*   [ ] **Streaming Responses:** Update the frontend and API gateway to support server-sent events (SSE) for real-time word streaming from the LLM.
*   [ ] **Hybrid Search:** Combine Qdrant's dense vector search with sparse keyword search (BM25 or Qdrant Sparse Vectors) to improve retrieval recall on exact product codes or names.
*   [ ] **Document Versioning:** Implement metadata version tracking in Qdrant payloads to handle document updates, overwrites, and deletion cycles gracefully.

---

## Phase 4: Multi-Tenant Architecture & Global Scale

*   [ ] **Logical Vector Partitioning:** Implement tenant-based metadata filtering within a shared Qdrant collection to guarantee data isolation.
*   [ ] **Distributed Ingestion Clusters:** Partition ingestion tasks across dynamically scaled worker nodes based on queue size.
*   [ ] **Enterprise Admin Dashboard:** Build a separate dashboard for administrators to monitor collection sizes, tenant token usage, and system latency.
*   [ ] **Multi-Modal Support:** Extend document loaders to parse and embed images, diagrams, and tables within PDFs using multi-modal models (e.g., Llama-3-Vision).
