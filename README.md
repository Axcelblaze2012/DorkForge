<div align="center">

# ⚡ DorkForge

### Forge Queries. Uncover Intelligence.

**An open-source, multi-engine search and OSINT research platform.**

Advanced Search · Search Intelligence · Security Research · Information Discovery

[Features](#-features) · [Installation](#-installation) · [Architecture](#-architecture) · [Documentation](#-api-documentation) · [Roadmap](#-roadmap) · [Contributing](#-contributing)

---

**Python 3.11+** · **FastAPI** · **React** · **TypeScript** · **SearXNG** · **Docker**

</div>

## 🔍 Overview

**DorkForge** is an open-source search platform designed to make advanced web discovery more powerful, precise, and accessible.

Unlike traditional Google dork collections that simply redirect users to external search engines, DorkForge provides an integrated search experience with structured query processing, multi-provider search orchestration, result validation, and an extensible backend architecture.

Built for cybersecurity researchers, OSINT practitioners, developers, and advanced search enthusiasts, DorkForge brings powerful search capabilities into a unified research environment.

The project began as **Dork Atlas**, a browser-based Google dork workbench, and is evolving into a comprehensive search intelligence platform.

### Why DorkForge?

Traditional search engines are designed primarily for general information retrieval. Advanced research often requires greater control over search operators, data sources, result filtering, and query execution.

DorkForge aims to bridge that gap by providing:

- **Precision:** Advanced search operators and structured query validation.
- **Flexibility:** Multiple search providers through a modular architecture.
- **Transparency:** Search diagnostics, provider attribution, and explainable filtering.
- **Control:** Self-hosted search infrastructure and configurable providers.
- **Extensibility:** A modular foundation for future AI-assisted research and independent indexing.

> **Our mission:** Make advanced search more transparent, accessible, and useful for legitimate security research and public-information discovery.

---

## ✨ Features

### 🔎 Multi-Engine Search

Execute searches directly within DorkForge without being forced to open external search engines.

**Capabilities:**

- Integrated search results interface
- SearXNG metasearch integration
- Optional Brave Search API integration
- Results from multiple underlying search engines
- Configurable search providers
- Provider health checks
- Provider timeout handling
- Result normalization
- URL deduplication
- Relevance scoring
- Search pagination
- Provider attribution

DorkForge can retrieve results through SearXNG, which aggregates compatible search engines such as Google, DuckDuckGo, Brave, and others according to the SearXNG instance configuration.

**Note:** Individual engine availability depends on the configured SearXNG instance, network conditions, and upstream provider restrictions.

### ⚙️ Advanced Dork Query Engine

DorkForge features a structured search query engine designed for advanced search syntax.

Supported query capabilities include:

| Operator | Purpose | Example |
|---|---|---|
| `site:` | Restrict searches to a domain | `site:example.com` |
| `filetype:` | Filter document formats | `filetype:pdf` |
| `intitle:` | Search within page titles | `intitle:documentation` |
| `inurl:` | Match URL patterns | `inurl:/docs` |
| `intext:` | Search page content | `intext:security` |
| `before:` | Filter by date | `before:2025-01-01` |
| `after:` | Filter by date | `after:2024-01-01` |
| `OR` | Boolean alternatives | `security OR privacy` |
| `-` | Exclude terms | `documentation -archive` |
| `"..."` | Exact phrase matching | `"security policy"` |

The query engine also recognizes provider-dependent operators such as `related:` and `AROUND(n)`.

**Important:** Operator support varies across search providers. DorkForge uses query translation and compatibility diagnostics to identify limitations rather than assuming all engines support identical syntax.

### 🛡️ Strict Search Result Verification

DorkForge includes a structured result-validation system designed to improve advanced-search precision.

The validation pipeline evaluates supported query constraints against available result metadata.

Results can be classified as:

| Status | Description |
|---|---|
| **Verified** | Available evidence satisfies the enforced constraints |
| **Unverified** | Insufficient information to confirm all constraints |
| **Rejected** | Available evidence violates one or more constraints |

**Validation capabilities include:**

- Domain and subdomain matching
- Lookalike-domain rejection
- URL pattern matching
- Page-title verification
- Document-type verification where metadata is sufficient
- Boolean query evaluation
- Exclusion handling
- Query constraint diagnostics

DorkForge provides **Strict** and **Relaxed** search modes.

Strict mode prioritizes results that satisfy verifiable constraints. Relaxed mode allows broader candidate discovery.

Some operators require information that search providers do not return. Such constraints may remain unverified without additional source inspection.

### 🧠 Structured Query Processing

At the core of DorkForge is a query-processing architecture built around a structured Abstract Syntax Tree (AST).

The processing system includes:

- Query tokenization
- Recursive-descent parsing
- Syntax validation
- Structured AST generation
- Boolean expression handling
- Provider-aware translation
- Operator compatibility checks
- Query diagnostics

**Search processing pipeline:**

```text
                    USER QUERY
                        │
                        ▼
                  QUERY PARSER
                        │
                        ▼
                 QUERY AST ENGINE
                        │
                        ▼
               PROVIDER TRANSLATOR
                        │
                        ▼
               SEARCH ORCHESTRATOR
                        │
              ┌─────────┴─────────┐
              │                   │
              ▼                   ▼
            SearXNG             Brave API
              │                 (Optional)
              │                   │
              └─────────┬─────────┘
                        │
                        ▼
                RESULT NORMALIZER
                        │
                        ▼
                  DEDUPLICATION
                        │
                        ▼
               CONSTRAINT VALIDATION
                        │
                        ▼
                  RESULT RANKING
                        │
                        ▼
                    PAGINATION
                        │
                        ▼
                 DORKFORGE RESULTS
```

### 📚 Built-in Dork Library

DorkForge preserves the original collection of **56 curated search presets** organized into six categories.

| Category | Presets |
|---|---:|
| Site Discovery | 9 |
| Public Documents | 11 |
| Technology | 10 |
| Content Research | 10 |
| Security & Policy | 10 |
| Learning | 6 |
| **Total** | **56** |

Library functionality includes:

- Browse built-in presets
- Search and filter presets
- Generate queries from templates
- Save custom presets
- Manage favorites
- Reuse previous searches
- Copy generated queries
- Organize research workflows

### 📊 Search Diagnostics

DorkForge provides visibility into how searches are processed.

Available diagnostic information includes:

- Active search operators
- Provider compatibility
- Search execution time
- Provider response status
- Retrieved candidate counts
- Verified result counts
- Rejected and unverified candidates
- Locally enforced constraints
- Unsupported operator warnings
- Result-filtering explanations

This helps distinguish between unavailable results, unsupported operators, and results rejected by strict validation.

### 💾 Persistent Research Data

DorkForge supports persistent application data using SQLite for local development and PostgreSQL for more advanced deployments.

Data-management capabilities include:

- Saved search history
- Custom query presets
- Favorites
- Provider configurations
- Search execution metadata
- Data export
- Legacy data migration

The application includes a migration mechanism for importing data from the original Dork Atlas browser-based application.

### 🔐 Security-Conscious Architecture

Security considerations are integrated into the application design.

The backend includes mechanisms for:

- Input validation
- API rate limiting
- Security headers
- Controlled external requests
- Provider timeout handling
- Server-side API credential management
- Safe query processing
- Local development configuration

DorkForge is intended for public-information research and authorized security assessments.

---

## 🏗️ Architecture

DorkForge uses a modular frontend/backend architecture.

### Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript, Vite |
| Styling | Tailwind CSS |
| State Management | Zustand |
| Backend | Python, FastAPI |
| API Validation | Pydantic |
| Database ORM | SQLAlchemy |
| Local Database | SQLite |
| Production Database | PostgreSQL |
| Metasearch | SearXNG |
| Optional Search API | Brave Search API |
| Infrastructure | Docker, Docker Compose |
| Frontend Testing | Vitest |
| Backend Testing | Pytest |

### Project Structure

```text
DorkForge/
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── data/
│   │   ├── features/
│   │   ├── hooks/
│   │   ├── lib/
│   │   ├── services/
│   │   └── stores/
│   ├── tests/
│   └── package.json
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   ├── core/
│   │   ├── database/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── search/
│   │   └── services/
│   └── tests/
│
├── infrastructure/
│   ├── docker/
│   ├── searxng/
│   └── compose.yaml
│
├── scripts/
│   ├── setup.sh
│   ├── dev.sh
│   └── test.sh
│
├── docs/
├── legacy/
│
├── .env.example
├── .gitignore
├── DEVELOPMENT_STATUS.md
├── README.md
└── package.json
```

---

## 🚀 Installation

### Prerequisites

Before installing DorkForge, ensure your system has:

| Requirement | Version |
|---|---|
| Operating System | Linux or macOS |
| Node.js | 18+ |
| Python | 3.11+ |
| npm | Compatible with installed Node.js |
| Git | Recent stable version |
| Docker | Optional |
| Docker Compose | Optional |

The project is developed primarily for Ubuntu Linux.

### 1. Clone the Repository

```bash
git clone https://github.com/Axcelblaze2012/DorkForge.git

cd DorkForge
```

### 2. Run Automated Setup

```bash
chmod +x scripts/setup.sh

./scripts/setup.sh
```

The setup script installs the required development dependencies and prepares the backend environment.

### 3. Configure Environment Variables

Copy the example configuration:

```bash
cp .env.example .env
```

Open the configuration file:

```bash
nano .env
```

Example search-provider configuration:

```env
# SearXNG
DORK_ATLAS_SEARXNG_URL=http://localhost:8080

# Optional Brave Search API
DORK_ATLAS_BRAVE_API_KEY=

# Database
# See .env.example for supported database settings.
```

**Compatibility note:** The project currently uses legacy `DORK_ATLAS_*` environment-variable names. These are retained for compatibility during the transition to DorkForge.

Existing database settings and provider configurations should not be renamed without implementing a corresponding migration.

---

## 🔌 Search Provider Setup

### Option 1 — SearXNG (Recommended)

SearXNG is a free, open-source metasearch engine that can aggregate results from multiple external search engines.

DorkForge includes a Docker Compose configuration for running a local instance.

Start SearXNG:

```bash
docker compose -f infrastructure/compose.yaml up -d searxng
```

Verify that the container is running:

```bash
docker compose -f infrastructure/compose.yaml ps
```

Open the SearXNG interface:

```text
http://localhost:8080
```

Test the JSON API:

```bash
curl -G http://localhost:8080/search \
  --data-urlencode "q=OWASP Top 10" \
  --data-urlencode "format=json"
```

A successful request should return a JSON response containing search results when the configured underlying engines are available.

**Note:** JSON response format must be enabled in the SearXNG configuration.

### Connecting SearXNG to DorkForge

Configure:

```env
DORK_ATLAS_SEARXNG_URL=http://localhost:8080
```

For a backend running directly on the host, use the host-accessible SearXNG URL.

For the backend running within the bundled Docker Compose network, use:

```text
http://searxng:8080
```

Provider endpoints can also be configured through the application's provider management API.

### Option 2 — Brave Search API

DorkForge supports an optional Brave Search API adapter.

To enable it, obtain an API key from the official Brave Search API service.

Add the key to your environment configuration:

```env
DORK_ATLAS_BRAVE_API_KEY=YOUR_API_KEY_HERE
```

Never commit actual API credentials to Git.

**Brave Search API is optional.** DorkForge can perform searches through a functioning SearXNG instance without a standalone Brave API key.

### Option 3 — External Google Search

DorkForge retains the ability to open generated queries directly in Google Search.

This is an optional fallback for users who want to execute searches outside the application.

---

## 💻 Running DorkForge

### Start the Development Environment

Run:

```bash
./scripts/dev.sh
```

This starts the local development services configured by the project.

Default addresses:

| Service | Address |
|---|---|
| Frontend | http://localhost:5173 |
| Backend | http://localhost:8000 |
| FastAPI Documentation | http://localhost:8000/docs |
| SearXNG | http://localhost:8080 |

### Manual Startup

**Backend:**

```bash
backend/.venv/bin/uvicorn app.main:app \
  --app-dir backend \
  --reload \
  --port 8000
```

**Frontend:**

```bash
npm --prefix frontend run dev
```

Run these commands in separate terminal sessions.

Ensure SearXNG or another configured search provider is accessible before testing external search functionality.

---

## 🔎 Usage Examples

### Basic Search

```text
OWASP Top 10
```

Search for publicly available information using configured search providers.

### Domain-Specific Search

```text
site:owasp.org "OWASP Top 10"
```

Restrict a search to a specific domain.

### Document Discovery

```text
site:owasp.org filetype:pdf
```

Discover publicly indexed PDF documents where supported by the selected engine.

### Title-Based Search

```text
site:docs.python.org intitle:asyncio
```

Search for relevant Python documentation pages by title.

### URL-Based Search

```text
site:docs.python.org inurl:library
```

Filter results using URL constraints.

### Boolean Search

```text
site:owasp.org ("security" OR "privacy")
```

Search using grouped alternatives.

### Search Execution

After entering a query:

1. Select the desired search settings.
2. Review operator compatibility warnings.
3. Select Strict or Relaxed search mode.
4. Click **Run on Atlas** (legacy interface label).
5. Review results and diagnostic information.

---

## 🧪 Testing

DorkForge includes automated frontend and backend tests.

### Run All Tests

```bash
./scripts/test.sh
```

### Frontend Tests

```bash
npm --prefix frontend run test
```

### Backend Tests

```bash
backend/.venv/bin/python -m pytest backend/tests -v
```

### Production Frontend Build

```bash
npm --prefix frontend run build
```

### Test Coverage Areas

The test suites cover functionality such as:

- Query parsing
- Domain normalization
- Operator validation
- Boolean expression handling
- Search request processing
- Provider orchestration
- Search result matching
- URL normalization
- Preset preservation
- API integration
- Frontend query construction

Automated tests primarily validate deterministic application behavior.

Live search functionality additionally depends on external search-provider availability and configuration.

---

## 🔗 API Documentation

DorkForge provides a REST API built with FastAPI.

Interactive documentation is available at:

```text
http://localhost:8000/docs
```

### Core API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/search` | Execute a search |
| `POST` | `/api/v1/search/composer` | Build a structured search |
| `GET` | `/api/v1/search/history` | Retrieve search history |
| `GET` | `/api/v1/providers` | List search providers |
| `PATCH` | `/api/v1/providers/{provider_id}` | Update provider configuration |
| `POST` | `/api/v1/providers/{provider_id}/test` | Test provider connectivity |

### Example API Request

```bash
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "OWASP Top 10",
    "mode": "universal",
    "providers": ["searxng-local"],
    "strict": true,
    "page": 1,
    "per_page": 10,
    "save_history": false
  }'
```

The response includes search results, provider execution information, and available diagnostics.

Refer to the OpenAPI documentation for complete request and response schemas.

---

## 🗺️ Roadmap

DorkForge is an evolving project.

The following roadmap outlines the long-term vision. Features listed as planned should not be interpreted as already implemented.

| Phase | Development Focus | Status |
|---|---|---|
| Phase 1 | Search engine foundation | Core functionality implemented |
| Phase 2 | Advanced operator validation | Implemented; ongoing refinement |
| Phase 3 | Multi-engine management | Planned / incremental development |
| Phase 4 | AI-assisted search intelligence | Planned |
| Phase 5 | OSINT research workspaces | Planned |
| Phase 6 | Independent web crawler | Planned |
| Phase 7 | Independent search index | Planned |
| Phase 8 | Production hardening and ecosystem | Planned |

### Future Capabilities

**AI Search Intelligence**
- Natural-language query generation
- Query optimization
- AI-assisted result analysis
- Source-backed research summaries
- Configurable AI providers

**Professional OSINT Workspaces**
- Domain intelligence
- Research collections
- Saved evidence
- Document analysis
- Relationship visualization
- Research reports

**Independent Search Infrastructure**
- Controlled web crawling
- Document extraction
- Full-text indexing
- Custom ranking
- Independent searchable collections

**Developer Ecosystem**
- Extended API integrations
- Search-provider plugins
- Custom query templates
- Improved documentation
- Community contributions

For detailed implementation progress, see `DEVELOPMENT_STATUS.md`.

---

## 🤝 Contributing

Contributions, bug reports, feature requests, and documentation improvements are welcome.

To contribute:

1. Fork the repository.
2. Create a feature branch.
3. Make your changes.
4. Add relevant tests.
5. Verify existing functionality.
6. Submit a pull request describing your changes.

Example:

```bash
git checkout -b feature/search-improvement

git add .

git commit -m "feat: improve search functionality"

git push origin feature/search-improvement
```

### Contribution Guidelines

Please follow these principles:

- Maintain modular architecture.
- Preserve backward compatibility where practical.
- Avoid introducing unnecessary dependencies.
- Add tests for new functionality.
- Never commit secrets or credentials.
- Respect search provider terms and limitations.
- Follow responsible security research practices.

---

## 🔒 Responsible Use

DorkForge is intended for educational, research, and authorized security-assessment purposes.

Advanced search operators can reveal publicly indexed information, but public availability does not automatically establish permission to access, download, or redistribute sensitive data.

Users are responsible for ensuring their activities comply with applicable laws, website policies, and authorization requirements.

DorkForge does not grant permission to access systems, accounts, or information without authorization.

**Use responsibly. Research ethically. Respect privacy.**

---

## 🐛 Bug Reports & Feature Requests

Found a bug or have an idea?

Open a GitHub issue:

**https://github.com/Axcelblaze2012/DorkForge/issues**

When reporting a bug, include:

- A clear description
- Steps to reproduce
- Expected behavior
- Actual behavior
- Relevant logs
- Operating system and runtime versions

Never include credentials, API keys, or sensitive information in public issues.

---

## 📄 License

DorkForge is distributed under the **MIT License**.

See the `LICENSE` file for the complete license text.

---

## ⭐ Support the Project

If you find DorkForge useful, consider:

- Starring the repository
- Reporting bugs
- Suggesting features
- Improving documentation
- Contributing code
- Sharing the project with other researchers and developers

Community contributions help make DorkForge more useful, reliable, and accessible.

---

<div align="center">

### ⚡ DorkForge

**Forge Queries. Uncover Intelligence.**

*Search deeper. Research smarter. Build independently.*

**Open Source · Advanced Search · OSINT Research**

[GitHub Repository](https://github.com/Axcelblaze2012/DorkForge)

</div>
