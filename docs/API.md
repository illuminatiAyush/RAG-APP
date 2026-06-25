# API Reference & Event Contract Specification

This document details the interface schemas, endpoints, and Inngest event payloads utilized in the application.

---

## 1. FastAPI Routes

### Inngest Endpoint

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| **GET** | `/api/inngest` | Returns server environment and registered schemas for Inngest dev dashboard. | No |
| **POST** | `/api/inngest` | Receives incoming actions and executes tasks/steps. | Yes (in production via signing keys) |
| **PUT** | `/api/inngest` | Registers or updates job configurations on the dev server. | No |

---

## 2. Inngest Event Payloads

### Event: `rag/ingest_pdf`
Processes a document, segments it into semantic chunks, generates vector embeddings locally, and indexes them in the Qdrant DB.

#### Event Schema Details
*   **Trigger Event Name:** `rag/ingest_pdf`
*   **Throttling:** Max 2 invocations per minute (`Throttle(count=2, period=1m)`).
*   **Rate Limiting:** Max 1 invocation per 4 hours per file (`RateLimit(limit=1, period=4h, key="event.data.pdf_path")`) to prevent duplicate processing of the same file.

#### Payload Structure
```json
{
  "name": "rag/ingest_pdf",
  "data": {
    "pdf_path": "C:\\Users\\ritik\\Downloads\\day-1.pdf",
    "source_id": "day-1.pdf"
  }
}
```

#### Step Outputs

##### Step 1: `load-and-chunks`
Returns the extracted and partitioned text chunks.
*   **Schema Class:** `RAGChunkAndSrc`

```json
{
  "chunks": [
    "Text chunk 1 containing document introduction...",
    "Text chunk 2 containing core system concepts..."
  ],
  "source_id": "day-1.pdf"
}
```

##### Step 2: `embed-and-upsert`
Confirms the number of successfully indexed chunks.
*   **Schema Class:** `RAGUpsertResult`

```json
{
  "ingested": 2
}
```

---

### Event: `rag/query_pdf_ai`
Performs a semantic vector search across the knowledge base and invokes Groq (Llama-3) to synthesize a grounded answer.

#### Event Schema Details
*   **Trigger Event Name:** `rag/query_pdf_ai`

#### Payload Structure
```json
{
  "name": "rag/query_pdf_ai",
  "data": {
    "question": "What is the primary motivation behind context engineering?",
    "top_k": 5
  }
}
```

#### Step Outputs

##### Step 1: `embed-and-search`
Returns matching context blocks from Qdrant.
*   **Schema Class:** `RAGSearchResult`

```json
{
  "contexts": [
    "Effective context engineering ensures the model receives a dense, high-signal payload...",
    "The quality of AI-generated code depends less on prompt cleverness and more on context..."
  ],
  "sources": [
    "day-1.pdf"
  ]
}
```

##### Step 2: `llm-answer` (AI Inference Step)
Invokes `ctx.step.ai.infer` using Groq's Llama 3 model endpoint.

*   **Final Output JSON:**
```json
{
  "answer": "Context engineering is motivated by the realization that LLM generation quality depends highly on dense, high-signal inputs (knowledge, examples, tools) rather than prompt cleverness.",
  "sources": [
    "day-1.pdf"
  ],
  "num_contexts": 2
}
```

---

## 3. Data Models (Pydantic Schemas)

All data structures are validated using Pydantic in [`app/custom_types.py`](file:///c:/Users/ritik/OneDrive/Desktop/RAGProducitonApp/app/custom_types.py).

### Schema Table

| Model Class | Attribute | Type | Description |
| :--- | :--- | :--- | :--- |
| **RAGChunkAndSrc** | `chunks` | `list[str]` | The semantic string sections extracted from the parsed document. |
| | `source_id` | `Optional[str]` | The unique filename or identifier of the source document. Default: `None`. |
| **RAGUpsertResult** | `ingested` | `int` | The total number of point structs successfully upserted into Qdrant. |
| **RAGSearchResult** | `contexts` | `list[str]` | Text contexts retrieved from vector database. |
| | `sources` | `list[str]` | Source filenames representing the retrieved contexts. |
| **RAGQueryResult** | `answer` | `str` | Synthesized answer from the LLM. |
| | `sources` | `list[str]` | Associated source references used for grounding the response. |
| | `num_contexts` | `int` | Count of retrieved contexts passed to the model. |

---

## 4. API Error Specifications

| HTTP Status | Error Type | Cause | Recommended Action |
| :--- | :--- | :--- | :--- |
| **400 Bad Request** | `PydanticValidationError` | Missing required payload parameters (e.g., missing `pdf_path` in ingestion). | Check payload key-value naming and types. |
| **401 Unauthorized** | `AuthenticationError` | Missing/invalid `GROK_API_KEY` or signing key signature. | Set the `GROK_API_KEY` environment variable. |
| **404 Not Found** | `NoSuchFileError` | The file path specified in `pdf_path` does not exist on the filesystem. | Verify path exists and file permissions permit reading. |
| **429 Too Many Requests** | `InngestThrottled` | Client exceeded the 2 PDF ingestions/minute throttle limit. | Implement backoff in client and retry after delay. |
| **500 Internal Error** | `QdrantConnectionError` | The local Qdrant instance is offline or unreachable. | Run `docker ps` to verify the Qdrant container is active. |
