# Production Deployment Guide

This guide details the procedures for deploying the RAG Production Engine to cloud environments (Railway, Render, AWS, GCP, Kubernetes).

---

## 1. Production Architecture (Target State)

In production, decouple the server nodes to prevent heavy CPU-bound parsing/embedding tasks from blocking HTTP client traffic:

```
                  ┌──────────────────────┐
                  │   Streamlit Frontend │
                  └──────────┬───────────┘
                             │ HTTP
                             ▼
                  ┌──────────────────────┐
                  │  FastAPI Gateway API │
                  └──────────┬───────────┘
                             │
            ┌────────────────┴────────────────┐
            ▼                                 ▼
┌──────────────────────┐           ┌──────────────────────┐
│  Inngest Cloud Agent │           │ Qdrant Vector Cluster│
└──────────┬───────────┘           └──────────▲───────────┘
           │                                  │
           │ HTTP Event                       │ gRPC
           ▼                                  │
┌──────────────────────┐                      │
│ Background Workers   ├──────────────────────┘
│ (Celery / VM / GPU)  │
└──────────────────────┘
```

---

## 2. Production Environment Variables

Ensure these keys are configured securely in your target cloud provider:

| Variable | Description | Recommended Production Value |
| :--- | :--- | :--- |
| `GROK_API_KEY` | Groq API access token. | `gsk_prod_...` (Store as Secret) |
| `INNGEST_SIGNING_KEY` | Verification key for Inngest event payloads. | High-entropy string (Store as Secret) |
| `QDRANT_URL` | Endpoint of the persistent Qdrant service. | `https://your-qdrant-cluster.com` |
| `QDRANT_API_KEY` | Read/write API token for Qdrant database. | Strong secret token |
| `ENVIRONMENT` | Running context. | `production` |

---

## 3. Deployment Targets

### 3.1. Deployment to Railway / Render (Easiest)
Railway and Render support automatic deployment from GitHub using a Dockerfile.

1.  **FastAPI Backend Container:**
    *   Deploy as a Web Service.
    *   Command: `uv run uvicorn app.main:app --host 0.0.0.0 --port $PORT`
    *   Configure public domain forwarding for the `/api/inngest` route so Inngest Cloud can reach your worker.
2.  **Inngest Integration:**
    *   Add your public backend domain (e.g., `https://your-api.railway.app/api/inngest`) inside your Inngest Cloud dashboard to register the event handlers.
3.  **Qdrant Database:**
    *   Deploy the official `qdrant/qdrant` image as a private, disk-persisted service inside your private network. Set up a persistent volume mapped to `/qdrant/storage`.

---

### 3.2. Kubernetes Deployment (Enterprise)
For high-availability, run the system in a Kubernetes cluster using separate deployments:

#### Backend Deployment Manifest (`backend-deployment.yaml`)
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rag-backend
  namespace: rag-prod
spec:
  replicas: 3
  selector:
    matchLabels:
      app: rag-backend
  template:
    metadata:
      labels:
        app: rag-backend
    spec:
      containers:
      - name: backend
        image: yourregistry/rag-backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: GROK_API_KEY
          valueFrom:
            secretKeyRef:
              name: rag-secrets
              key: grok-api-key
        resources:
          limits:
            cpu: "2"
            memory: 2Gi
          requests:
            cpu: "500m"
            memory: 512Mi
```

---

## 4. Monitoring & Observability

1.  **Distributed Tracing (OpenTelemetry):**
    *   Configure `FastAPI` and `Qdrant` clients to export metrics to Prometheus and Jaeger/Zipkin.
2.  **Inngest Run Logs:**
    *   Use Inngest Cloud's centralized observability dashboard to track run durations, cold starts, retry histories, and failure tracebacks.
3.  **Sentry Error Tracking:**
    *   Initialize Sentry in `app/main.py` to capture unhandled exceptions in real-time.

---

## 5. Backup & Disaster Recovery

### Qdrant Snapshots
To back up your vector indices without downtime, execute Qdrant's snapshot API:

```bash
# Create a snapshot of the docs collection
curl -X POST http://localhost:6333/collections/docs/snapshots \
     -H "api-key: $QDRANT_API_KEY"
```

Save the resulting `.snapshot` file to offsite cold storage (such as AWS S3 or GCP Cloud Storage) on a daily cron schedule. In the event of a catastrophic host failure, restore the database structure:

```bash
# Restore collection from a snapshot file
curl -X POST http://localhost:6333/collections/docs/snapshots/recover \
     -H "Content-Type: application/json" \
     -H "api-key: $QDRANT_API_KEY" \
     -d '{"location": "https://s3.amazonaws.com/your-backups/docs-2026.snapshot"}'
```
