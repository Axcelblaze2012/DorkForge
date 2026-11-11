# Dork Atlas Ultimate

> **Advanced Search. Intelligence Discovery. Independent Research.**

Dork Atlas Ultimate is a modular, production-oriented search engine and OSINT research platform. It transforms the original Google dork workbench into a full-stack search engine with its own query-processing architecture, multi-provider search orchestration, structured query parser and AST, persistent preset library, and research workbench.

---

## Key Features

- **In-App Search Execution**: Execute real searches directly inside Dork Atlas without forced Google redirects, querying configured engines like SearXNG and Brave Search API.
- **Advanced Query Engine**: Structured recursive-descent lexer and parser producing an explainable AST, validating syntax, checking operator compatibility, and translating dorks across engines.
- **Original Preset Preservation**: All 56 built-in presets across the original 6 categories (*Site Discovery, Public Documents, Technology, Content Research, Security & Policy, Learning*) are fully preserved and seeded into the persistent database.
- **One-Time Zero-Loss Migration**: Automatically imports legacy browser data (`dork-atlas-favorites-v1`, `dork-atlas-custom-v1`, `dork-atlas-recent-v1`) into the SQLite/PostgreSQL database idempotently.
- **Multi-Provider Search Orchestration**: Concurrent query translation, provider isolation, URL normalization, deduplication, and explainable scoring and ranking.
- **Persistent Search History**: Tracks executed searches, parsed operators, provider latencies, and result counts with data export capabilities.
- **Secure by Default**: Strict input validation, SSRF boundaries, rate limiting, security headers, unexposed provider credentials, and single-user local development mode.

---

## Architecture Overview

```
DORK-ATLAS-ULTIMATE/
├── frontend/                # React 18 + TypeScript + Vite + Tailwind CSS + Zustand
│   ├── src/
│   │   ├── components/      # UI primitives, layout, modal, toast
│   │   ├── data/            # Builtin preset definitions (56 presets)
│   │   ├── features/        # Query composer, search results, presets, history, settings
│   │   ├── hooks/           # Server probe, hotkeys, search lifecycle
│   │   ├── lib/             # Query builder, domain normalization, tokenization
│   │   ├── services/        # Type-safe API client
│   │   └── stores/          # Zustand store with persistence & migration
│   └── tests/               # Vitest unit test suite
├── backend/                 # Python 3.11+ FastAPI + SQLAlchemy + SQLite/PostgreSQL
│   ├── app/
│   │   ├── api/v1/          # REST API endpoints (search, presets, history, providers, migration)
│   │   ├── core/            # Config, security middleware, logging
│   │   ├── database/        # Async session & engine management
│   │   ├── models/          # SQLAlchemy declarative models
│   │   ├── schemas/         # Pydantic request/response schemas
│   │   ├── search/          # AST parser, lexer, engine translator, orchestrator, ranking
│   │   └── services/        # Presets, providers, history, seeder
│   └── tests/               # Pytest suite (API integration + parser AST tests)
├── infrastructure/          # Docker Compose & SearXNG configuration
└── scripts/                 # Dev and test automation scripts
```

---

## Requirements

- **Linux / macOS**: Developed and tested on Linux (Ubuntu).
- **Node.js**: v18+ (tested on Node v22).
- **Python**: 3.11+ (tested on Python 3.14).
- **Docker** (optional): For self-hosting SearXNG container.

---

## Installation & Setup

1. **Clone the repository and enter the directory**:
   ```bash
   cd DORK-ATLAS-ULTIMATE
   ```

2. **Automated setup**:
   ```bash
   ./scripts/setup.sh
   ```
   This creates `backend/.venv`, installs all backend dependencies, and installs all frontend dependencies.

3. **Environment configuration**:
   ```bash
   cp .env.example .env
   ```
   Customize `.env` if using a remote SearXNG instance or Brave Search API key.

---

## Running Locally

To start both the FastAPI backend (`http://127.0.0.1:8000`) and the Vite React frontend (`http://127.0.0.1:5173`) with a single command:

```bash
./scripts/dev.sh
```

Or run them individually:

- **Backend**:
  ```bash
  backend/.venv/bin/uvicorn app.main:app --app-dir backend --reload --port 8000
  ```
- **Frontend**:
  ```bash
  npm --prefix frontend run dev
  ```

---

## Search Provider Configuration

Dork Atlas supports multiple search providers:

1. **SearXNG (Self-Hosted / Containerized)**:
   - Run the bundled Docker Compose profile:
     ```bash
     docker compose -f infrastructure/compose.yaml up -d searxng
     ```
   - In `.env`, set `DORK_ATLAS_SEARXNG_URL=http://localhost:8080`.
2. **Brave Search API**:
   - In `.env`, provide `DORK_ATLAS_BRAVE_API_KEY=<your-key>`.
   - The Brave adapter will automatically activate in the provider registry.
3. **Google External Fallback**:
   - The UI includes the direct Google Search button to launch queries in a separate tab without server-side scraping.

---

## Running Automated Tests

Run the complete frontend and backend test suites:

```bash
./scripts/test.sh
```

Or run them individually:

```bash
# Frontend tests (Vitest)
npm run test:frontend

# Backend tests (Pytest)
npm run test:backend
```

---

## License

MIT License. Responsible use: search public information only and restrict active security research to authorized scopes.
