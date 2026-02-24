# Meeting → Actions AI Service

## Overview

A full-stack application that converts raw meeting transcripts into structured, trackable action items using Large Language Models. Upload a meeting transcript, review the AI's proposed changes side-by-side with the current project state, and approve or request revisions before anything is committed.

The project demonstrates:

- REST API design (FastAPI + Pydantic)
- Backend architecture and separation of concerns
- Data modeling and validation (SQLAlchemy + SQLite)
- AI integration patterns (OpenAI / Anthropic, with mock mode for local development)
- React frontend with a proposal-based review workflow
- Docker Compose for single-command setup

---

## What the Service Does

The API accepts a **full meeting transcript** (plain text) and extracts structured action items such as:

- Tasks
- Decisions
- Follow-ups
- Questions

Each action is returned with a confidence score and a normalized schema suitable for downstream systems like project management tools or analytics pipelines.

### Example Input

```
Sarah will investigate the API issue.
Elena and David need to sync on S3 permissions.
```

### Example Output

```json
[
  {
    "type": "task",
    "description": "Sarah to investigate the API issue",
    "confidence": 0.98
  },
  {
    "type": "task",
    "description": "Elena and David to sync on S3 permissions",
    "confidence": 0.95
  }
]
```

---


## Architecture

```
Browser (React SPA)
        |
        v   http://localhost:3000
React Frontend
        |
        v   http://localhost:8000
FastAPI Backend
├── Routes (HTTP layer)
│   ├── /projects            # Project CRUD, list
│   ├── /meetings            # Meeting creation and processing
│   ├── /actions             # Action retrieval, update, delete
│   └── /reconcile           # AI proposal & apply workflow
│
├── Services (Business logic)
│   ├── ActionExtractor      # Extract actions from transcript
│   └── ProjectReconciler    # Reconcile new transcript against existing actions
│
├── Models (SQLAlchemy ORM)
│   ├── Project
│   ├── Meeting
│   └── Action
│
├── Schemas (Pydantic)
│   ├── Request validation
│   └── Response serialization
│
└── SQLite Database (persisted via Docker volume)
```

---

## Project Structure

```
├── app/                           # Backend (FastAPI)
│   ├── main.py                    # Application entrypoint
│   ├── config.py                  # Environment-based configuration
│   ├── database.py                # Database engine and session management
│   ├── models.py                  # SQLAlchemy ORM models
│   ├── schemas.py                 # Pydantic request/response schemas
│   ├── routes/
│   │   ├── projects.py            # Project + reconciliation endpoints
│   │   ├── meetings.py            # Meeting creation and processing
│   │   └── actions.py             # Action update and delete
│   └── services/
│       ├── action_extractor.py    # AI extraction logic
│       ├── project_reconciler.py  # Proposal / apply reconciliation
│       └── report_generator.py    # Markdown report generation
│
├── frontend/                      # Frontend (React + Vite)
│   ├── src/
│   │   ├── App.tsx                # Router setup
│   │   ├── api.ts                 # Backend API client
│   │   └── pages/
│   │       ├── ProjectList.tsx    # Project listing and creation
│   │       └── ProjectDashboard.tsx  # Transcript upload, proposal review, actions
│   ├── Dockerfile                 # Multi-stage Node build + serve
│   └── package.json
│
├── Sample Transcripts/            # Example meeting transcripts (5 projects)
├── Dockerfile                     # Backend Docker image
├── docker-compose.yml             # Full-stack orchestration
├── requirements.txt               # Python dependencies
├── .env.example                   # Environment variable template
└── README.md
```

---

## Core Concepts

### REST API Design

- Clear resource-oriented endpoints
- Proper HTTP verbs and status codes
- Stateless request handling

### FastAPI + Pydantic

- Automatic request parsing
- Automatic response serialization
- Strict input/output validation
- Strong typing at API boundaries

### Status-Based Processing Model

Meetings progress through a defined lifecycle:

```
PENDING → PROCESSING → DONE / FAILED
```

This ensures:

- Idempotent processing
- Clear system state
- Easier debugging and observability

---

## AI Integration Strategy

The service supports LLM-based extraction via:

- OpenAI
- Anthropic

For local development and portfolio usage, the project includes a **mock extraction mode**.

### Mock Mode Behavior

- Automatically enabled when no API key is present
- Returns deterministic, structured action items
- Enables full API testing without cost or external dependencies

This approach allows the system to remain fully functional while keeping AI concerns isolated.

---

## Quick Start (Docker)

The recommended way to run the full application. Requires **Docker** and **Docker Compose**.

### 1. Clone and configure

```bash
git clone https://github.com/khalidtahir/Meeting-Actions-API
cd Meeting-Actions-API

cp .env.example .env
```

Open `.env` and set your OpenAI API key:

```
OPENAI_API_KEY=sk-...
```

> Without `OPENAI_API_KEY`, the app runs in **mock mode** -- all AI features return deterministic placeholder responses so you can explore the UI without any external API calls.

### 2. Build and start

```bash
docker compose up --build
```

This builds both images, starts the API, waits for its health check to pass, then starts the frontend. First build takes a few minutes; subsequent runs are cached.

### 3. Open the app

| Service | URL | Notes |
|---------|-----|-------|
| **Frontend** | http://localhost:3000 | React app -- start here |
| **API** | http://localhost:8000 | FastAPI backend |
| **API Docs** | http://localhost:8000/docs | Interactive OpenAPI / Swagger UI |

### 4. Verify everything is working

```bash
# Both containers should show as running (api should be "healthy")
docker compose ps

# API health check
curl http://localhost:8000/health
# → {"status":"healthy","database":"connected","ai_provider":"openai"}

# API logs
docker compose logs api

# Frontend logs
docker compose logs frontend
```

Open http://localhost:3000 in your browser. You should see the project list page (empty on first run). Create a project, open it, and paste a sample transcript from the `Sample Transcripts/` directory to test the full workflow.

### Stopping and restarting

```bash
# Stop all containers
docker compose down

# Stop and remove stored data (SQLite database)
docker compose down -v

# Restart without rebuilding
docker compose up -d
```

SQLite data is persisted in a Docker volume (`api_data`), so project and action data survive normal restarts. Use `down -v` only when you want a clean slate.

---

## Running Without Docker (manual setup)

If you prefer to run the backend and frontend directly on your machine.

### Backend

Requires **Python 3.10+**.

```bash
cp .env.example .env
# Edit .env and set OPENAI_API_KEY (optional)

python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux

pip install -r requirements.txt
cd app
uvicorn main:app --host 0.0.0.0 --port 8000
```

API will be available at http://localhost:8000 (docs at http://localhost:8000/docs).

### Frontend

Requires **Node.js 18+**.

```bash
cd frontend
npm install
npm run dev
```

Opens at http://localhost:5173 by default (Vite dev server). Set `VITE_API_URL` if the backend runs on a different host:

```bash
VITE_API_URL=http://localhost:8000 npm run dev
```

---

## Example Workflow

1. **Create a project** -- give it a name and optional description.
2. **Upload a meeting transcript** -- paste the raw meeting minutes and click "Generate proposal."
3. **Review the AI proposal** -- see current open actions side-by-side with proposed completions, carryovers, and new items.
4. **Approve or reject** -- approve to commit changes to the database, or reject with feedback and the AI will revise its proposal.
5. **Track action items** -- view all actions grouped by owner, manually add or edit items, and upload subsequent meeting transcripts to keep the project up to date.

Sample transcripts for five fictional projects are included in `Sample Transcripts/` to get started quickly.

---

## Future Extensions

- Background processing (Celery / Redis)
- Authentication and authorization (JWT)
- Real-time meeting ingestion
- Integration with Jira / Linear
- Organization and user scoping
- Cost and usage tracking
- Vector search and retrieval-augmented generation (RAG)

---



## License

MIT License

Copyright (c) 2026 Khalid Tahir

This repository is open-source. Future hosted products, infrastructure, and proprietary extensions may remain closed-source.

---

## Author

**Khalid Tahir**  
Computer Engineering, Queen’s University  
Backend Systems • APIs • AI-Assisted Applications

