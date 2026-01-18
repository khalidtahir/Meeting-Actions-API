# Meeting → Actions AI Service

## Overview

The **Meeting → Actions AI Service** is a backend-focused REST API that converts raw meeting transcripts into structured, actionable items using Large Language Models (LLMs).

This project was built as a **portfolio-grade backend MVP** to demonstrate strong fundamentals in:

- REST API design
- Backend architecture and separation of concerns
- Data modeling and validation
- AI integration patterns (with safe mocking for local development)
- Production-aware design decisions

The service is intentionally scoped to remain clear, testable, and extensible.

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

## What This Project Is Not

- Not a real-time transcription system
- Not a frontend application
- Not a fully deployed SaaS product

This repository represents a **backend MVP**, optimized for clarity, correctness, and interview discussion.

---

## Architecture

```
Client (Postman / curl)
        |
        v
FastAPI Application
├── Routes (HTTP layer)
│   ├── /meetings
│   └── /actions
│
├── Services (Business logic)
│   └── ActionExtractor
│
├── Models (SQLAlchemy ORM)
│   ├── Meeting
│   └── Action
│
├── Schemas (Pydantic)
│   ├── Request validation
│   └── Response serialization
│
└── SQLite Database
```

---

## Project Structure

```
app/
├── main.py                  # Application entrypoint
├── config.py                # Environment-based configuration
├── database.py              # Database engine and session management
├── models.py                # SQLAlchemy ORM models
├── schemas.py               # Pydantic request/response schemas
├── routes/
│   ├── meetings.py          # Meeting creation and processing endpoints
│   └── actions.py           # Action retrieval endpoints
└── services/
    └── action_extractor.py  # AI and mock extraction logic

requirements.txt
.env.example
README.md
LICENSE
```

---

## Core Technical Concepts Demonstrated

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

## Running the Project Locally

### Prerequisites

- Python 3.10+

### Setup

```bash
git clone https://github.com/khalidtahir/Meeting-Actions-API
cd Meeting-Actions-API

python -m venv venv
venv\Scripts\activate   # Windows

python -m pip install -r requirements.txt
python app/main.py
```

### API Documentation

Interactive OpenAPI documentation is available at:

```
http://localhost:8000/docs
```

---

## Example Workflow

1. Create a meeting
2. Trigger transcript processing
3. Retrieve extracted actions

This mirrors real-world asynchronous workflows while remaining synchronous for simplicity.

---

## Design Decisions and Tradeoffs

### Why FastAPI

- High performance
- First-class typing support
- Built-in OpenAPI generation
- Clean dependency injection

### Why SQLite

- Zero configuration
- Ideal for MVPs and interviews
- Easily replaceable with PostgreSQL for production

### Why Synchronous Processing

- Simplifies control flow
- Easier to debug and test
- Clear upgrade path to background jobs

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

## Interview Talking Points

- Clear separation between HTTP, business logic, and data layers
- Status-driven processing to avoid race conditions
- Mockable AI layer for testability and cost control
- Designed for extensibility without over-engineering

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

