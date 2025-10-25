Temporalified RAG System

Overview
- This scaffolds a simple RAG pipeline orchestrated with Temporal (workflows + activities).
- It parses the HTML notebook in the repo, builds a lightweight local index, retrieves top chunks for a query, and synthesizes a stubbed answer.
- Swap the stubbed generator and index with real LLM/vector DB as needed.

Structure
- `temporal_rag/src/activities.py` — Activities: parse HTML, chunk, build index, retrieve, synthesize
- `temporal_rag/src/workflows.py` — Workflow orchestrating the RAG steps
- `temporal_rag/src/worker.py` — Temporal Worker registering workflow + activities
- `temporal_rag/src/client.py` — Simple CLI client to run the workflow
- `temporal_rag/requirements.txt` — Python dependencies

Prereqs
- Python 3.10+
- Temporal server reachable (local dev or cloud). For local dev you can use:
  - Temporal CLI: `temporal server start-dev`
  - Or Docker: `docker run --name temporal -p 7233:7233 temporalio/auto-setup:latest`
- Install deps: `python -m venv .venv && source .venv/bin/activate && pip install -r temporal_rag/requirements.txt`

Configuration
- Env vars:
  - `TEMPORAL_ADDRESS` (default: `localhost:7233`)
  - `TASK_QUEUE` (default: `rag-task-queue`)
  - `RAG_HTML_PATH` (default: `JHU_AgenticAI_Project_1_Learners_Notebook.html`)
  - `TOP_K` (default: `5`)
  - `CHUNK_SIZE` (default: `1200` characters)
  - `CHUNK_OVERLAP` (default: `200` characters)

Run (dev)
1) Start Temporal dev server: `temporal server start-dev`
2) In a new shell: `source .venv/bin/activate`
3) Start worker: `python -m temporal_rag.src.worker`
4) In another shell: run a query
   - `python -m temporal_rag.src.client --question "What is covered in the notebook?"`

Notes
- The current generator is a deterministic stub to keep the scaffold dependency-light. Replace `synthesize_answer` with a real LLM call (e.g., OpenAI) once configured.
- The index is a naive inverted index with token overlap scoring. Replace with a vector DB (e.g., FAISS, PGVector, Milvus) by swapping `build_index` and `retrieve` activities.

