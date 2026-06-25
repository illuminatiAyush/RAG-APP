# Local Development & Environment Setup Guide

Follow this guide to set up the local development environment for the RAG Production Engine on your machine.

---

## 1. Prerequisites

Ensure your machine meets the following baseline tool requirements:
*   **Operating System:** Windows 10/11, macOS 13+, or Linux (Ubuntu 22.04+)
*   **Docker Desktop:** Required to run the local Qdrant Vector database instance.
*   **NodeJS (v18+):** Required for the Inngest CLI/Dev agent.
*   **Git:** To manage source versioning.

---

## 2. Dependency Tooling Installation

### Step A: Install Python 3.11
We recommend running Python 3.11.

*   **macOS (via Homebrew):**
    ```bash
    brew install python@3.11
    ```
*   **Windows (via winget):**
    ```powershell
    winget install Python.Python.3.11
    ```
*   **Linux (Ubuntu/Debian):**
    ```bash
    sudo apt update
    sudo apt install python3.11 python3.11-venv -y
    ```

### Step B: Install `uv` (Rust-based Python Package Installer)
`uv` is highly recommended for sub-second package resolution.

*   **macOS / Linux:**
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```
*   **Windows:**
    ```powershell
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    ```

---

## 3. Local Workspace Setup

### Step 1: Clone the Repository
```bash
git clone https://github.com/illuminatiAyush/RAG-APP.git
cd RAG-APP
```

### Step 2: Establish the Virtual Environment
Create a virtual environment and synchronize dependencies:
```bash
# Creates .venv/ and installs all dependencies from pyproject.toml / uv.lock
uv sync
```

### Step 3: Configure Environment
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Open the `.env` file and insert your Groq API Key:
```env
GROK_API_KEY=gsk_your_actual_key_here
```

---

## 4. Spin Up Infrastructure Services

### Service A: Qdrant Vector Database
Run the local Qdrant container with data persistence mapped to your local workspace:
```bash
# Command for macOS / Linux / PowerShell (maps current working directory)
docker run -d --name qdrant_dev -p 6333:6333 -p 6334:6334 -v "$(pwd)/qdrant_storage:/qdrant/storage" qdrant/qdrant
```

### Service B: Inngest Dev Server
Start the Inngest local development agent to route background jobs:
```bash
npx inngest-cli@latest dev
```
Once started, the Inngest Dashboard will be accessible at: `http://localhost:8288`

---

## 5. Launch the Application

For a fully working setup, launch both the backend API server and the Streamlit frontend client.

### Part 1: Start FastAPI Web Server
Run Uvicorn to host FastAPI and serve the Inngest endpoint:
```bash
uv run uvicorn app.main:app --reload --port 8000
```
This registers the application route `/api/inngest` with Inngest dev server. Verify registration at `http://localhost:8288`.

### Part 2: Start Streamlit Frontend Client
In a new terminal tab, launch the Streamlit frontend:
```bash
uv run streamlit run streamlit_app.py
```
This launches the application UI dashboard at: `http://localhost:8501`

---

## 6. Troubleshooting Common Issues

### Issue 1: Address already in use (`Errno 10048` or `Port 8000 is occupied`)
*   **Cause:** A previous instance of `uvicorn` is still running in the background.
*   **Fix (macOS/Linux):**
    ```bash
    kill -9 $(lsof -t -i:8000)
    ```
*   **Fix (Windows PowerShell):**
    ```powershell
    Stop-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess -Force
    ```

### Issue 2: Qdrant connection times out
*   **Cause:** Qdrant container is not running or blocked by a local firewall.
*   **Fix:** Check running containers using `docker ps`. If the container `qdrant_dev` is stopped, run `docker start qdrant_dev`.

### Issue 3: Inngest CLI fails to discover handlers
*   **Cause:** FastAPI application is not running or Inngest served path `/api/inngest` returned an error.
*   **Fix:** Ensure your FastAPI app compiles cleanly (`python -m py_compile app/main.py`) and is hosted on port 8000.
