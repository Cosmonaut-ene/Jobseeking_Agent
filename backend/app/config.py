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


# Scraper defaults
DEFAULT_MAX_JOBS: int = int(os.environ.get("DEFAULT_MAX_JOBS", "15"))

# Tailor evaluator-optimizer loop (SPEC 附录 F.5 TASK-C04)
# deterministic_ats_score（0-100）达到此阈值即停止迭代；反馈信号用确定性分数，不用 LLM 自评
TAILOR_DETERMINISTIC_THRESHOLD: float = float(os.environ.get("TAILOR_DETERMINISTIC_THRESHOLD", "80"))
TAILOR_MAX_ITERATIONS: int = int(os.environ.get("TAILOR_MAX_ITERATIONS", "2"))
