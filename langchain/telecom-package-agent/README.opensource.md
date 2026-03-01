# Telecom Package Agent (Open Source Edition)

Production-style demo for AI-assisted telecom customer operations:
- Phone number lifecycle management
- Package lifecycle management
- User-package binding with validity windows
- Benefits and usage operations
- Agent-driven chat, complaints, and reminders

## Contents
- Project Scope
- Functional Business Flow
- System Architecture Flow
- Key Modules
- API Surface
- Local Development
- Contribution Guide
- Open-Source Release Checklist

## Project Scope
This project is designed as a full-stack reference for:
- Telecom customer support automation
- LLM intent-routing and domain handling
- FastAPI + React integration patterns
- Operable management pages for real workflows

## Functional Business Flow

```mermaid
flowchart TD
    OP[Operator / Admin] --> U1[Phone Number Management]
    OP --> P1[Package Management]
    U1 --> DBU[(User Table)]
    P1 --> DBP[(Package Table)]

    OP --> BIND[Bind Package to Phone]
    BIND --> REL[(UserPackage Relation)]
    REL --> VALID{Validity Window<br/>start_date <= now < end_date}

    CUST[End User] --> CHAT[Web Chat]
    CHAT --> INTENT{Intent Router}

    INTENT --> I1[Package Query / Recommend]
    INTENT --> I2[Usage Query / Warning / Top-up]
    INTENT --> I3[Benefits Query / Claim]
    INTENT --> I4[Package Change]
    INTENT --> I5[Complaint / Human Escalation]
    INTENT --> I6[Renewal Reminder]

    I1 --> DBP
    I1 --> REL
    I2 --> DBU
    I3 --> DBU
    I4 --> REL
    I5 --> DBC[(Complaint Table)]
    I6 --> REL

    CHAT --> RESP[Structured Response + Suggestions]
```

## System Architecture Flow

```mermaid
flowchart LR
    subgraph Client
        BROWSER[Browser]
        FE[React + Vite Frontend]
    end

    subgraph API
        FASTAPI[FastAPI App]
        ROUTER[API Routers<br/>users/packages/benefits/usage/chat]
    end

    subgraph Agent
        CHATAPI[Chat Endpoint]
        AGENT[TelecomAgent]
        ROUTE[Global Intent Routing]
        HANDLERS[Domain Handlers<br/>package/usage/benefit/change/complaint/reminder]
        TOOLS[LangChain Tools]
    end

    subgraph Data
        MYSQL[(MySQL)]
        REDIS[(Redis)]
    end

    subgraph LLM
        OPENAI[OpenAI-Compatible LLM]
    end

    BROWSER --> FE
    FE --> FASTAPI
    FASTAPI --> ROUTER

    ROUTER --> MYSQL
    ROUTER --> CHATAPI
    CHATAPI --> AGENT
    AGENT --> ROUTE
    ROUTE --> HANDLERS
    AGENT --> TOOLS
    HANDLERS --> MYSQL
    TOOLS --> MYSQL
    AGENT <--> REDIS
    AGENT --> OPENAI

    FASTAPI --> FE
```

## Key Modules
- Backend:
  - `backend/app/api`: REST APIs
  - `backend/app/agent`: chat agent, prompt, tools, intent handlers
  - `backend/app/services`: core business logic
  - `backend/app/models`: SQLAlchemy models
- Frontend:
  - `frontend/src/pages/Users`: phone number management
  - `frontend/src/pages/Packages`: package management + binding
  - `frontend/src/pages/Chat`: agent interaction
  - `frontend/src/pages/Dashboard`: operational metrics view

## API Surface
Main prefix: `/api/v1`

- Users / phone numbers: `/users`
- Packages: `/packages`
- User package relation:
  - `/users/{user_id}/packages/current`
  - `/users/{user_id}/packages/history`
  - `/users/{user_id}/packages/assign`
- Benefits: `/benefits/*`
- Usage: `/usage/*`
- Chat:
  - `/chat`
  - `/chat/transfer-human`
  - `/chat/history/{session_id}`

For detailed scenario matrix:
- [docs/agent-scenarios.md](docs/agent-scenarios.md)

## Local Development

1. Backend
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Database migration (from repository root)
```bash
mysql -u root -p < scripts/init_db.sql
PYTHONPATH=backend backend/.venv/bin/python -m alembic upgrade head
```

3. Start backend
```bash
cd backend
./start start
```

4. Frontend
```bash
cd frontend
yarn install
yarn dev
```

## Contribution Guide
- Fork the repository
- Create a feature branch
- Keep changes scoped and documented
- Run build checks before PR:
  - `python3 -m compileall backend/app`
  - `yarn --cwd frontend build`
- Open PR with:
  - problem statement
  - change summary
  - verification notes

## Open-Source Release Checklist
- [ ] Add a `LICENSE` file (required before public distribution)
- [ ] Add repository topics and tags
- [ ] Add CI checks (lint/build/tests)
- [ ] Add issue/PR templates
- [ ] Add `SECURITY.md` and `CODE_OF_CONDUCT.md` (recommended)

---

If you prefer the default project README with bilingual quick-start:
- [README.md](README.md)
