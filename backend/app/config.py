"""Centralised configuration — reads from environment / .env file."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Paths
BASE_DIR = Path(__file__).parents[2]  # Jobseeking_Agent/
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "db" / "jobseeking.db"
PROFILE_PATH = DATA_DIR / "user_profile.json"
COOKIES_DIR = DATA_DIR / "cookies"
RESUMES_DIR = DATA_DIR / "resumes"
COVER_LETTERS_DIR = DATA_DIR / "cover_letters"

# API Keys
GEMINI_API_KEY: str = os.environ.get("GEMINI_API_KEY", "")

# Notification webhook (Telegram bot webhook or any HTTP endpoint)
NOTIFICATION_WEBHOOK_URL: str = os.environ.get("NOTIFICATION_WEBHOOK_URL", "")
NOTIFICATION_CHAT_ID: str = os.environ.get("NOTIFICATION_CHAT_ID", "")

# Matching thresholds
HIGH_SCORE_THRESHOLD: float = float(os.environ.get("HIGH_SCORE_THRESHOLD", "0.80"))
MID_SCORE_THRESHOLD: float = float(os.environ.get("MID_SCORE_THRESHOLD", "0.70"))

# Scheduler
SCHEDULER_HOUR: int = int(os.environ.get("SCHEDULER_HOUR", "9"))
SCHEDULER_MINUTE: int = int(os.environ.get("SCHEDULER_MINUTE", "0"))
SCHEDULER_ENABLED: bool = os.environ.get("SCHEDULER_ENABLED", "true").lower() == "true"

# Scraper defaults
DEFAULT_MAX_JOBS: int = int(os.environ.get("DEFAULT_MAX_JOBS", "15"))
