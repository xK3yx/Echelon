# Echelon

**AI-assisted career intelligence.** Describe your skills, personality, and interests; Echelon ranks career paths against your profile using a deterministic rule engine followed by a Groq LLM re-ranker, generates a per-career skill-gap analysis with a three-phase learning roadmap, recommends YouTube playlist courses to bridge each gap, and lets you keep the conversation going with **Vantage**, an AI career-counsellor chatbot. When no strong match is found, a Stage 2.5 LLM proposal step generates speculative career suggestions tailored to your profile.

> **About this project**
> Echelon began as my final-year project for the **Diploma in Information Technology** at SEGi College Kota Damansara. This repository is a refined and substantially expanded follow-on to that submission — adding resume import, dark mode, course recommendations, public share links, PDF export, an onboarding tour, deployment configs, the Vantage chatbot, and full multimodal attachment handling. The original academic version has been preserved in the v2 / v2.1 git history; the current `main` is v2.2.

---

## Features

| Feature | Details |
|---|---|
| **Profile-driven matching** | Multi-step form captures skills, interests, education, and Big Five personality scores. A deterministic rule engine scores ~25 curated tech-adjacent careers (plus optional O\*NET ingestion) on weighted skill, personality, and interest dimensions. |
| **Two-stage LLM ranking** | Top-10 rule candidates re-ranked by `llama-3.3-70b-versatile` with explicit guidance to question narrow-specialty bias. Returns top 5 with fit reasoning, strengths, risks, and confidence. |
| **Speculative career proposal** | When no rule score clears the threshold, a Stage 2.5 LLM generates novel career suggestions from your profile combination, persisted with a clear "AI Suggested" badge. |
| **Skill gaps + learning roadmap** | Per-career: gap skills tagged easy / medium / hard by `llama-3.1-8b-instant`, plus a three-phase Beginner / Intermediate / Advanced roadmap. |
| **Resume import** | Upload PDF, DOCX, or TXT to pre-fill the form. Multi-stage validation: size → MIME (libmagic) → text extraction (pypdf, pdfplumber fallback for graphically-designed CVs, python-docx) → heuristic resume detection → structured LLM extraction → confidence threshold. |
| **YouTube playlist courses** | Each career card has a "Bridge the gap" section. YouTube provider returns full course **playlists** (not single videos); Tavily provider adds curated platforms (Udemy, Coursera, edX, freeCodeCamp). LLM ranks the combined pool and picks the 5 most relevant. Cached per career for 7 days. |
| **Vantage chatbot** | Floating chat widget on the results page. Knows your full profile and recommendation context, answers follow-ups ("why is full-stack ranked above frontend?", "what should I learn first?"), and accepts attachments — PDFs, DOCXs, TXT files (text-extracted into context) and images (sent to a Groq vision model). |
| **Public share links** | One-click Share button copies a `/r/{id}` URL to the clipboard; the public page renders the full analysis without authentication. |
| **PDF export** | Print-ready A4 report via WeasyPrint — includes score breakdown, skill gaps, and full roadmap. Rendered off the event loop. |
| **"How we scored this"** | Four-bar score breakdown surfacing rule sub-scores (skill 45 / optional 15 / personality 25 / interests 15) plus total rule score and LLM confidence, with inline tooltips explaining what each number means. |
| **Dark / light / system theme** | Persisted via `next-themes`. Affects every page and the Vantage widget. |
| **Onboarding tour** | First-visit four-step react-joyride walkthrough on the profile page. Dismissible; flag stored in `localStorage`. |

---

## Tech stack

**Backend** — FastAPI 0.111 · SQLAlchemy 2 (async) · Alembic · Pydantic v2 · PostgreSQL 15 · WeasyPrint + Jinja2 · pypdf / pdfplumber / python-docx / python-magic · slowapi · httpx
**LLM** — Groq Cloud (`llama-3.3-70b-versatile` for ranking + chat, `llama-3.1-8b-instant` for extraction tasks, `meta-llama/llama-4-scout-17b-16e-instruct` for Vantage vision messages)
**Frontend** — Next.js 14 (App Router) · TypeScript strict · Tailwind CSS · shadcn/ui · TanStack Query · React Hook Form · Zod · next-themes · react-joyride · lucide-react
**Infra** — Docker Compose for local dev · Railway (backend + Postgres) · Vercel (frontend)

---

## Data sources

| Badge | Source | Notes |
|---|---|---|
| **O\*NET** | [O\*NET OnLine](https://www.onetonline.org/) — U.S. Department of Labor | ~200 knowledge-work occupations from O\*NET 28.x+. Optional ingestion via `make ingest-onet`. US-centric; international titles may differ. |
| **Curated** | Hand-authored entries in `backend/app/seed/careers.json` | ~25 tech-adjacent roles. Loaded via `make seed`. Supplements O\*NET. |
| **Proposed** | LLM-generated when no O\*NET / curated career matches well | Speculative, displayed with a warning badge. Not promoted into the catalogue without admin review. |
| **YouTube** | YouTube Data API v3 | Full course playlists. No partnership with YouTube or creators. |
| **Tavily** | Tavily Search API | Web results from Udemy, Coursera, edX, Pluralsight, LinkedIn Learning, freeCodeCamp, Skillshare, DataCamp, Kaggle, YouTube. |

**O\*NET attribution (CC BY 4.0 — required):**
> "This product uses data from O\*NET OnLine by the U.S. Department of Labor, Employment and Training Administration (USDOL/ETA). O\*NET® is a trademark of USDOL/ETA."

---

## Honest disclaimers

- **Academic / portfolio project** — built originally as a diploma final-year project and refined since. Not validated by career counsellors or industry research, and not a production product.
- **Curated dataset** — the career database covers ~25 hand-authored roles by default plus optional O\*NET ingestion. It does not cover every career.
- **LLM non-determinism** — rankings, reasoning, roadmaps, and Vantage replies come from Groq. Identical inputs may produce different outputs. The "Re-run" button intentionally exploits this.
- **Resume parsing is heuristic** — accuracy depends on file quality and formatting. Always review pre-filled fields before submitting.
- **Confidence scores are approximations** — the rule-based score is a weighted sum of categorical matches; the LLM confidence is a model self-assessment. Neither is a statistically validated predictor of career success.
- **Vantage is an assistant, not an advisor** — it answers questions about your specific recommendation, but its replies are AI-generated estimates.
- **No authentication** — profile submissions and recommendations are anonymous. Possession of a recommendation UUID is enough to view, share, export, or chat. Do not submit real personal data.
- **No partnerships** — Echelon has no relationships with YouTube, Tavily, course creators, employers, or educational institutions.
- **Not career advice** — output is illustrative. Consult a qualified career advisor before making major decisions.

---

## Architecture

```
Browser (Next.js 14 App Router)
    │
    ├─ /                 → landing page, dark-mode toggle
    ├─ /profile          → multi-step form, resume upload, onboarding tour
    ├─ /results/{id}     → career cards, course playlists, share / PDF buttons, Vantage widget
    └─ /r/{id}           → public share page (no auth required)
    │
    │  POST /api/profiles
    │  POST /api/recommendations
    │  GET  /api/recommendations/{id}
    │  POST /api/recommendations/{id}/share
    │  GET  /api/recommendations/{id}/public
    │  GET  /api/recommendations/{id}/pdf
    │  POST /api/resume/parse
    │  GET  /api/courses/recommend
    │  GET  /api/chat/{recommendation_id}/messages
    │  POST /api/chat/{recommendation_id}/messages   (multipart: text + optional file)
    ▼
FastAPI (Python 3.11)
    │
    ├─ Stage 1: Rule scoring (deterministic)
    │    skill × 0.45 + optional × 0.15 + personality × 0.25 + interest × 0.15
    │    Education soft penalty: high_school + high-difficulty career → score × 0.7
    │    Top 10 candidates passed to Stage 2
    │
    ├─ Stage 2: Groq re-rank (llama-3.3-70b-versatile, temp 0.3)
    │    Returns top 5 with fit_reasoning, strengths, risks, confidence
    │    Prompt explicitly warns against narrow-specialty over-fitting
    │
    ├─ Stage 2.5: LLM career proposal (only when top score < propose_threshold)
    │    Generates speculative careers not in the database
    │
    ├─ Stage 3: Batched gap tagging + roadmap
    │    3-phase roadmap per career; skill difficulty tagged by llama-3.1-8b-instant
    │
    ├─ Resume parsing: size → MIME → extract → heuristic → LLM → confidence threshold
    │
    ├─ Course recommendations: parallel YouTube + Tavily → URL dedup → LLM rank → 7-day cache
    │
    └─ Vantage chat: load history → build context (profile + recommendation + last 12 turns)
                     → process attachment (text extract or base64-image) → Groq → persist both turns
    │
    PostgreSQL (SQLAlchemy async + Alembic migrations)
       tables: users · profiles · careers · recommendations · course_cache · chat_messages
```

---

## Required environment variables

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | Yes | PostgreSQL connection string (`postgresql+asyncpg://...`) |
| `GROQ_API_KEY` | Yes | Groq API key — [console.groq.com](https://console.groq.com) |
| `ADMIN_TOKEN` | Recommended | Secret token for admin endpoints. Empty string disables admin routes. |
| `NEXT_PUBLIC_API_URL` | Yes (frontend) | Backend API base URL, e.g. `http://localhost:8000/api` |
| `PUBLIC_BASE_URL` | Production | Frontend origin, added to CORS allow-list, e.g. `https://echelon.vercel.app` |
| `YOUTUBE_API_KEY` | Optional | YouTube Data API v3. Course recommendations omit YouTube hits when absent. |
| `TAVILY_API_KEY` | Optional | Tavily Search API. Falls back to YouTube-only when absent. |
| `MAX_UPLOAD_SIZE_MB` | Optional | Max resume file size in MB (default `5`) |
| `RESUME_CONFIDENCE_THRESHOLD` | Optional | Combined parse confidence floor (default `0.4`) |
| `PROPOSE_THRESHOLD` | Optional | Rule score below which LLM career proposal triggers (default `0.4`) |
| `COURSE_CACHE_TTL_DAYS` | Optional | Days to cache course results per career slug (default `7`) |

Copy `.env.example` to `.env` and fill in the required values.

---

## Running locally

### Prerequisites

- Docker Desktop (or a local Postgres instance)
- Node.js 18+ for the frontend dev server

### Quick start

```bash
# 1. Clone and configure
git clone https://github.com/xK3yx/Echelon.git
cd Echelon
cp .env.example .env
# Edit .env — set DATABASE_URL and GROQ_API_KEY at minimum.
# Add YOUTUBE_API_KEY and TAVILY_API_KEY to enable the course section.

# 2. Build and start the backend + Postgres + frontend
docker compose up --build -d

# 3. Run migrations and seed the curated career list
make migrate
make seed

# 4. (Optional) Ingest the full O*NET catalogue for ~200 occupations
# Download O*NET 28.x+ text files from https://www.onetcenter.org/database.html
# Extract into ./data/onet/, then:
make ingest-onet ONET_DIR=/data/onet
```

Open [http://localhost:3000](http://localhost:3000).

### Running tests

```bash
make test
```

Tests require the backend container to be running (`docker compose up -d`). The pytest session finalizer cleans up Career rows created by integration test fixtures so the dev database stays uncluttered.

---

## Deployment

### Backend → Railway

1. Create a Railway project and add a Postgres plugin (provides `DATABASE_URL` automatically).
2. Point the service at this repo and set `RAILWAY_DOCKERFILE_PATH=backend/Dockerfile.production`.
3. Set the remaining environment variables in the Railway dashboard (`GROQ_API_KEY`, `ADMIN_TOKEN`, optional `YOUTUBE_API_KEY` / `TAVILY_API_KEY`, plus `PUBLIC_BASE_URL` once you know your Vercel URL).
4. Deploy. Migrations run automatically on startup (`alembic upgrade head`).

### Frontend → Vercel

1. Import the repository into Vercel and set the root directory to `frontend/`.
2. Add `NEXT_PUBLIC_API_URL` pointing to your Railway backend (e.g. `https://echelon-backend.up.railway.app/api`).
3. Deploy.

After both are live, set `PUBLIC_BASE_URL` on the Railway service to your Vercel URL so CORS allows the production frontend.

---

## API reference

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/health` | Liveness check, returns version |
| `POST` | `/api/profiles` | Create an anonymous profile |
| `GET` | `/api/profiles/{id}` | Read a profile |
| `GET` | `/api/profiles/{id}/matches` | Rule-based matches preview |
| `GET` | `/api/careers` | List all verified careers |
| `GET` | `/api/careers/{slug}` | Single career detail |
| `POST` | `/api/recommendations` | Run the full AI pipeline (Stage 1 → 2 → 2.5 → 3) |
| `GET` | `/api/recommendations/{id}` | Fetch a recommendation |
| `POST` | `/api/recommendations/{id}/share` | Mark as public |
| `GET` | `/api/recommendations/{id}/public` | Fetch without auth (requires `is_public = true`) |
| `GET` | `/api/recommendations/{id}/pdf` | Download PDF report |
| `POST` | `/api/resume/parse` | Parse a resume → structured profile fields |
| `GET` | `/api/courses/recommend` | Ranked course playlists for a career slug |
| `GET` | `/api/chat/{recommendation_id}/messages` | Vantage chat history |
| `POST` | `/api/chat/{recommendation_id}/messages` | Send a Vantage message (multipart, text + optional file) |
| `POST` | `/api/analyze` | Standalone gap analysis for a (profile, career) pair |

Admin endpoints (`/api/admin/...`) require `Authorization: Bearer <ADMIN_TOKEN>`.

---

## Limitations

- **US-centric career data** — O\*NET is a US government dataset. Job titles and skill expectations may differ in other countries.
- **No real-time labour market data** — salary ranges, demand trends, and hiring rates are not included.
- **LLM output is non-deterministic** — the same profile may produce different rankings across runs.
- **Resume parsing is heuristic** — accuracy depends on file quality and formatting. Scanned PDFs will fail; heavily styled CVs may need the pdfplumber fallback path.
- **Course relevance scores are estimates** — the LLM scores playlists from title, channel, and description snippet alone. It does not watch the content.
- **Vantage replies are AI-generated** — Vantage cites your profile and recommendation faithfully, but its phrasing and emphasis are model output, not professional advice.
- **No accessibility audit** — the UI has not been formally audited against WCAG 2.1.

---

## Licence and credits

This is an academic / portfolio project. Code in this repository is provided as-is for review and learning purposes. Career data attribution to O\*NET / U.S. Department of Labor (CC BY 4.0) is required wherever the dataset is used.

Originally submitted as my final-year project for the **Diploma in Information Technology** at **SEGi College Kota Damansara** (Final Semester 2026). The version on `main` is a substantially refined and expanded follow-on with features that were beyond the scope of the original submission.
