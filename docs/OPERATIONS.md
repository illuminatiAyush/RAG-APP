# System Operations & Runbook (SRE Manual)

This document contains standard operating procedures, metrics instrumentation, diagnostics, and failure recovery runbooks.

---

## 1. System Health Checks

To verify if the services are operational:

### 1.1. FastAPI Web Server Health
FastAPI is running and accepting event deliveries:
```bash
curl -I http://localhost:8000/api/inngest
# Target response: HTTP/1.1 200 OK or 405 Method Not Allowed (since GET is supported)
```

### 1.2. Inngest Connection Health
Verify that the Inngest Dev Server can communicate with the FastAPI server:
Check the logs of the `inngest-cli` dev agent. If it prints `apps synced, disabling auto-discovery`, the FastAPI app has successfully registered its handlers.

### 1.3. Qdrant Connection Health
Check if the local Qdrant container is online:
```bash
curl http://localhost:6333/healthz
# Target response: "status":"ok"
```

---

## 2. Monitoring & Instrumentation Metrics

For production deployments, monitor these key performance indicators (KPIs) to identify bottlenecks:

### 2.1. Ingestion Performance Metrics
Track these metrics using the structured logging markers we introduced:
*   **PDF Load Latency:** The time spent by `PDFReader().load_data()`. Spikes indicate slow storage IO.
*   **Chunking Latency:** The parsing duration of `SentenceSplitter`. 
*   **Embedding Latency:** Time taken by local `fastembed` model. High CPU utilization will cause spikes here.
*   **Qdrant Upsert Latency:** Time taken to write vectors to Qdrant. Spikes indicate network latency or Qdrant cluster saturation.

### 2.2. Query Performance Metrics
*   **Vector Search Latency:** Qdrant `query_points()` response time. Target: `<50ms`.
*   **LLM Inference Latency:** Groq API call time (`ctx.step.ai.infer`). Target: `<1.5s`.

---

## 3. Operational Runbooks (Failure Recovery)

### 3.1. Incident: Ingestion Fails with `400 Bad Request` or `401 Unauthorized`
*   **Symptom:** Inngest executions for `RAG: Ingest PDF` are failing or retrying with HTTP error statuses.
*   **Triage Commands:**
    1.  Check the environment variables:
        ```bash
        # Ensure GROK_API_KEY is not empty
        echo $GROK_API_KEY
        ```
    2.  Verify the `.env` file exists at the root:
        ```bash
        ls -la .env
        ```
    3.  Restart Uvicorn to ensure it loads the newest `.env` file.

### 3.2. Incident: Qdrant Database is Unreachable
*   **Symptom:** Ingestion logs print `ConnectionRefusedError` when connecting to `localhost:6333`.
*   **Triage Commands:**
    1.  Verify the Docker container is running:
        ```bash
        docker ps -f name=qdrant
        ```
    2.  If the container is stopped:
        ```bash
        docker start qdrant_dev
        ```
    3.  If Qdrant storage is corrupted or full, check disk usage:
        ```bash
        docker system df
        ```

### 3.3. Incident: LLM Inference Fails with `400`
*   **Symptom:** `llm-answer` step fails with status code `400` indicating model deprecation.
*   **Triage Commands:**
    1.  Query the Groq API `/models` endpoint to get the list of active models:
        ```bash
        curl https://api.groq.com/openai/v1/models \
             -H "Authorization: Bearer $GROK_API_KEY"
        ```
    2.  Verify if the model specified in `app/main.py` is still in the active models list. If not, update `app/main.py` to point to a supported model.
