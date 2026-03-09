# Jobseeking Agent

An AI-powered personal job search automation platform. It scrapes job boards daily, scores each listing against your resume, generates tailored application materials, and pushes instant notifications — with minimal daily effort required.

> **Stack**: FastAPI · SQLite · React · TypeScript · Tailwind · Gemini 2.5 Flash

---

## Features

### Job Discovery
- **Automated daily scraping** — Seek.com.au and Indeed.com.au via Playwright (configurable schedule)
- **LinkedIn support** — batch URL parsing (paste URLs, system scrapes details) + public RSS feed (no login required)
- **Manual entry** — paste any job description into the Scout page for instant analysis
- **Deduplication** — URL-based, skips already-seen jobs automatically

### AI Matching & Evaluation (Scout Agent)
- Parses raw job description → structured fields (title, company, location, salary, required skills)
- **5-section comprehensive evaluation report** per job:
  1. **Match Analysis** — ATS keyword match % + strong matches + missing skills + unmet requirements
  2. **Skills & Qualification Improvements** — technical skills, certifications, soft skills, tools (with explanations)
  3. **Resume Content Improvements** — bullet strength tips, achievements feedback, metrics suggestions, missing ATS keywords
  4. **Flow, Grammar & Formatting** — tone observations, action verb upgrades, layout suggestions
  5. **Overall Recommendations** — top 5 priority actions, quick wins (< 1 hour), deeper improvements, estimated score uplift %
- **Auto-filter** — discards jobs below `MID_SCORE_THRESHOLD` (default 70%), saves the rest
- **Instant push notification** for jobs above `HIGH_SCORE_THRESHOLD` (default 80%)

### Resume Tailoring
- Upload PDF/DOCX resume or paste text → AI extracts structured profile
- 6-tab profile editor (basics, skills, education, experience, projects, preferences)
- One-click LLM tailoring per job — keyword-optimised without fabrication
- ATS coverage score per tailored version
- Source traceability — every rewritten bullet linked to its original text
- **Download as Word (.docx)** for direct submission

### Cover Letter Generation
- Auto-generated from tailored resume + job description
- 3-paragraph format, under 250 words, with email subject line
- Application record created automatically on generation

### Application Tracking
- Job status lifecycle: `new → reviewed → applied → interview → offer / rejected / dismissed`
- Per-application notes, channel (email / easy apply / manual), follow-up dates
- Dashboard follow-up table flags overdue applications

### Dashboard & Analytics
- Stats by status, source, score tier (high / mid)
- Jobs added in the last 7 days
- **AI Advisor report** — top missing skills across all saved jobs, market summary, recommended actions

### Notifications
- Webhook push compatible with Telegram Bot API
- Immediate push on high-score job discovery
- Daily summary: scrape stats + top new jobs

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI 0.134, Uvicorn, SQLModel, SQLite |
| AI | Google Gemini 2.5 Flash (structured JSON output) |
| Scraping | Playwright (Seek, Indeed, LinkedIn URLs), httpx (LinkedIn RSS) |
| Scheduling | APScheduler |
| PDF/DOCX | pypdf, python-docx, WeasyPrint, Jinja2 |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, Axios |

---

## Prerequisites

- Python 3.12+
- Node.js 20+
- [Google Gemini API key](https://aistudio.google.com/app/apikey)

---

## Setup

### 1. Clone & install

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

```bash
cp .env.example .env   # or create manually
```

Edit `.env`:

```env
GEMINI_API_KEY=your_key_here

# Optional — Telegram-compatible webhook for push notifications
NOTIFICATION_WEBHOOK_URL=https://api.telegram.org/bot<token>/sendMessage
NOTIFICATION_CHAT_ID=your_chat_id

# Optional — override defaults
HIGH_SCORE_THRESHOLD=0.80
MID_SCORE_THRESHOLD=0.70
SCHEDULER_ENABLED=true
SCHEDULER_HOUR=9
SCHEDULER_MINUTE=0
DEFAULT_MAX_JOBS=15
```

### 3. Run

```bash
# Terminal 1 — backend
uvicorn backend.app.main:app --reload
# → http://localhost:8000  (API docs: /docs)

# Terminal 2 — frontend
cd frontend && npm run dev
# → http://localhost:5173
```

### 4. First-time setup

1. Open **Settings** → enter your Gemini API key
2. Open **Profile** → upload your resume PDF/DOCX or paste resume text
3. Review the extracted profile across all 6 tabs and save

---

## Usage

### Analyse a single job
Go to **Scout**, paste any job description, click **Analyse**. The AI returns a full 5-section evaluation report with an ATS match percentage and prioritised improvement actions.

### Scrape job boards
Go to **Scrapers**, enter keywords and location, click **Run** for Seek or Indeed. Jobs above the mid-score threshold are saved automatically; high-score jobs trigger an instant notification.

### Review & apply
Go to **Jobs** — filtered list of saved jobs sorted by score. Select a job to:
- View the full evaluation report ("View Full Evaluation")
- Approve / Dismiss
- **Tailor Resume** — generates a keyword-optimised version with ATS score
- **Download Word** — `.docx` ready for submission
- **Cover Letter** — generates email subject + 3-paragraph body

### Track applications
Update job status as you progress. The Dashboard shows pipeline stats and flags follow-ups that are due.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `GEMINI_API_KEY` | — | **Required.** Google Gemini API key |
| `NOTIFICATION_WEBHOOK_URL` | — | Telegram Bot API webhook URL |
| `NOTIFICATION_CHAT_ID` | — | Telegram chat / channel ID |
| `HIGH_SCORE_THRESHOLD` | `0.80` | ATS % threshold for instant push notification |
| `MID_SCORE_THRESHOLD` | `0.70` | Minimum ATS % to save a job |
| `SCHEDULER_ENABLED` | `true` | Enable daily auto-scrape |
| `SCHEDULER_HOUR` | `9` | Hour to run daily scrape (local time) |
| `SCHEDULER_MINUTE` | `0` | Minute to run daily scrape |
| `DEFAULT_MAX_JOBS` | `15` | Max results per scraper run |

---

## Docker

```bash
cp .env.example .env   # fill in GEMINI_API_KEY
docker compose up -d
# → http://localhost:8000
```

The `data/` directory is mounted as a volume — your database, profile, and generated files persist across restarts.

---

## Deployment (Render)

A `render.yaml` is included for one-click deployment to [Render](https://render.com):

1. Fork this repo
2. Create a new **Blueprint** in Render and connect your fork
3. Set `GEMINI_API_KEY` (and optionally notification vars) as environment secrets
4. Deploy — the build step installs dependencies, builds the frontend, and starts Uvicorn

A 1 GB persistent disk is attached at `data/` to preserve the database between deploys.

---

## Development

```bash
# Run tests
PYTHONPATH=. python3 -m pytest backend/tests/ -v

# TypeScript check
cd frontend && npx tsc --noEmit
```

- Branch naming: `feat/`, `fix/`, `chore/`, `refactor/` + short description
- PRs target `main`; never commit directly to `main`

---

## Data & Privacy

All data stays local (SQLite file at `data/db/jobseeking.db`). The only external calls are:
- Gemini API (job description text + resume profile sent for AI processing)
- Job board websites (scraping)
- Your configured notification webhook (job title, company, score)

No analytics, no third-party tracking.

---

## License

Personal use. Not licensed for redistribution.
