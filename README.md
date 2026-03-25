# Jobseeking Agent

> Built this tool to automate my own job search while applying for roles in Sydney's AI market. The manual process of screening listings, tailoring resumes, and tracking applications was time-consuming and inconsistent — so I automated it.

An AI-powered personal job search automation platform. It scrapes job boards daily, scores each listing against your resume with a detailed 5-section evaluation report, generates tailored application materials, and pushes instant notifications — requiring minimal daily effort.

> **Stack**: FastAPI · SQLite · React 18 · TypeScript · Tailwind CSS · Gemini 2.5 Flash

---

## Features

### Job Discovery
- **Seek.com.au** — Playwright-based scraper with keyword + location + date filters
- **Indeed.com.au** — Playwright-based scraper with keyword + location + date filters
- **LinkedIn** — No-login guest API scraper (zero account risk, no cookies required)
- **Manual entry** — Paste any job description into the Scout page for instant analysis
- **URL deduplication** — Already-seen jobs are skipped automatically
- **Scheduled daily scrape** — Runs all three sources at a configurable time (default 9:00 AM)

### AI Matching & Evaluation (Scout Agent)
Every job is evaluated against your profile by Gemini 2.5 Flash and produces a **5-section structured report**:

1. **Match Analysis** — ATS keyword match % · strong matches · missing skills · unmet hard requirements · summary
2. **Skills & Qualifications** — Technical skills to learn (with reasons) · certifications · soft skills · tools/platforms
3. **Resume Content** — Bullet strength tips · achievements vs duties feedback · metrics to add · exact ATS keywords missing from your resume
4. **Flow & Formatting** — Tone/clarity observations · weak-verb-to-strong-verb replacements · layout suggestions
5. **Recommendations** — Top 5 priority actions · quick wins (under 1 hour) · deeper improvements (1–4 weeks) · estimated ATS score uplift %

Jobs below `MID_SCORE_THRESHOLD` (default 70%) are automatically discarded. Jobs above `HIGH_SCORE_THRESHOLD` (default 80%) trigger an instant push notification.

### Resume Tailoring
- Upload resume — PDF, DOCX, DOC, TXT, or MD → AI extracts a structured profile
- Paste resume text → same extraction pipeline
- **Incremental merge** — re-uploading a newer resume merges into the existing profile without overwriting manual edits
- **6-tab profile editor** — Basic info · Skills (name / level / years) · Education · Experience · Projects · Preferences
- **One-click tailoring per job** — rewrites bullets and summary for ATS keyword alignment; never fabricates facts
- Every rewritten bullet includes its original source text for human review
- ATS coverage score per tailored version
- **Download as Word (.docx)** and as **PDF** for direct submission

### Cover Letter Generation
- Auto-generated from your tailored resume + job description
- 3 short paragraphs, under 250 words, with an email subject line
- Saves to `data/cover_letters/` as a `.txt` file
- Automatically records an application entry and sets a follow-up reminder 7 days out

### Application Tracking
- Status lifecycle: `new → reviewed → applied → interview → offer / rejected / dismissed`
- Per-application notes, channel, and follow-up date
- Dashboard surfaces overdue follow-ups

### Dashboard & Analytics
- Job counts by status, source, and score tier
- Jobs added in the last 7 days
- **AI Advisor report** — generated on demand; analyses all saved jobs to surface top missing skills, market summary, and recommended actions

### Notifications
- Sends via any **HTTP webhook** (payload format is Telegram Bot API compatible)
- **Immediate push** when a job scores ≥ 80% — sent within seconds of discovery
- **Daily summary** after the scheduled scout — scrape stats and top new jobs by score
- Manual test button in the UI to verify your webhook

---

## Tech Stack

| Layer | Technology | Version |
|---|---|---|
| Backend framework | FastAPI + Uvicorn | 0.134 / 0.41 |
| ORM / database | SQLModel + SQLite | 0.0.22 |
| AI | Google Gemini 2.5 Flash | google-genai ≥ 1.0 |
| Web scraping | Playwright (Chromium) | 1.40 |
| LinkedIn scraping | httpx + BeautifulSoup4 | guest API, no login |
| Scheduling | APScheduler | 3.10 |
| Resume parsing | pypdf + python-docx | 4.0 / 1.1 |
| PDF generation | WeasyPrint + Jinja2 | — |
| Frontend | React 18 + TypeScript | 18.3 / 5.4 |
| Build tool | Vite | 5.3 |
| Styling | Tailwind CSS | 3.4 |
| HTTP client (frontend) | Axios | 1.7 |

---

## Prerequisites

- Python 3.12+
- Node.js 20+
- [Google Gemini API key](https://aistudio.google.com/app/apikey)

---

## Setup

### 1. Clone and install

```bash
git clone https://github.com/Cosmonaut-ene/Jobseeking_Agent.git
cd Jobseeking_Agent

# Backend
pip install -r backend/requirements.txt
playwright install chromium

# Frontend
cd frontend && npm install && cd ..
```

### 2. Configure environment

Create a `.env` file in the project root:

```env
# Required
GEMINI_API_KEY=your_key_here

# Optional — push notifications (Telegram Bot API compatible webhook)
NOTIFICATION_WEBHOOK_URL=https://api.telegram.org/bot<token>/sendMessage
NOTIFICATION_CHAT_ID=your_chat_id

# Optional — thresholds (defaults shown)
HIGH_SCORE_THRESHOLD=0.80
MID_SCORE_THRESHOLD=0.70

# Optional — scheduler
SCHEDULER_ENABLED=true
SCHEDULER_HOUR=9
SCHEDULER_MINUTE=0
DEFAULT_MAX_JOBS=15
```

### 3. Start

```bash
# Terminal 1 — backend
uvicorn backend.app.main:app --reload
# API: http://localhost:8000   Docs: http://localhost:8000/docs

# Terminal 2 — frontend
cd frontend && npm run dev
# UI: http://localhost:5173
```

### 4. First-time setup

1. **Settings** → enter your Gemini API key (and optionally webhook URL)
2. **Resume** → upload your resume PDF/DOCX or paste resume text; review the extracted profile
3. **Profile** → fine-tune extracted data across all 6 tabs and save

---

## Usage

### Analyse a single job (Scout)
Paste any job description → **Analyse**. The 5-section evaluation report appears with ATS match %, prioritised actions, and missing keywords.

### Scrape job boards (Scrapers)
Enter keywords, location, and max results for Seek, Indeed, or LinkedIn. Results matching your thresholds are saved automatically; high-score jobs trigger an instant notification.

### Review and apply (Jobs)
- Select a job from the list to open the detail panel
- **Approve / Dismiss** to manage your pipeline
- **Tailor Resume** → generates an ATS-optimised version with a score and source-tracked bullets
- **Download Word / PDF** for submission
- **Cover Letter** → generates email subject + 3-paragraph body; records the application with a 7-day follow-up reminder
- **View Full Evaluation** → expands the complete 5-section report inline

### Track progress (Dashboard)
Monitor pipeline stats, check the AI Advisor report for skill gap insights, and review the follow-up table for overdue applications.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `GEMINI_API_KEY` | — | **Required.** Google Gemini API key |
| `NOTIFICATION_WEBHOOK_URL` | — | HTTP webhook for push notifications |
| `NOTIFICATION_CHAT_ID` | — | Optional `chat_id` field added to webhook payload |
| `HIGH_SCORE_THRESHOLD` | `0.80` | ATS score threshold for instant notification |
| `MID_SCORE_THRESHOLD` | `0.70` | Minimum score to save a job (below this is discarded) |
| `SCHEDULER_ENABLED` | `true` | Enable daily auto-scrape |
| `SCHEDULER_HOUR` | `9` | Hour to run the daily scrape (24-hour, local time) |
| `SCHEDULER_MINUTE` | `0` | Minute to run the daily scrape |
| `DEFAULT_MAX_JOBS` | `15` | Default max results per scraper run |

---

## Docker

```bash
cp .env.example .env   # set GEMINI_API_KEY
docker compose up -d
# http://localhost:8000
```

`data/` is mounted as a volume — your database, profile JSON, and generated files persist across restarts.

---

## Deploy to Render

A `render.yaml` is included for one-click deployment:

1. Fork this repo
2. Create a new **Blueprint** in [Render](https://render.com) and connect your fork
3. Set `GEMINI_API_KEY` (and optionally `NOTIFICATION_WEBHOOK_URL` / `NOTIFICATION_CHAT_ID`) as environment secrets
4. Deploy — Render builds the frontend, installs Chromium, and starts Uvicorn

A 1 GB persistent disk is attached at `data/` to keep your database between deploys.

---

## Development

```bash
# Run backend tests
PYTHONPATH=. python3 -m pytest backend/tests/ -v

# TypeScript type check
cd frontend && npx tsc --noEmit
```

Branch naming: `feat/`, `fix/`, `chore/`, `refactor/` + short hyphenated description. PRs target `main`; never commit directly to `main`.

---

## Data & Privacy

All data is stored locally in `data/db/jobseeking.db` (SQLite) and `data/user_profile.json`. The only external calls made are:

- **Gemini API** — job description text and your resume profile are sent for AI processing
- **Job board websites** — Seek, Indeed, LinkedIn (public pages only, no accounts)
- **Your configured webhook** — job title, company, and match score on high-score discoveries

No analytics, no telemetry, no third-party tracking.
