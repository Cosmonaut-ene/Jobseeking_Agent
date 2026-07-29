"""Independent database engine for the Analytics dashboard (TASK-D02).

Deliberately separate from backend/app/database.py's production engine —
the Analytics router must never read or write the production
data/db/jobseeking.db, only the synthetic data/analytics_demo.db produced
by scripts/generate_analytics_demo_data.py.
"""
from sqlmodel import create_engine

from backend.app.config import DATA_DIR

ANALYTICS_DB_PATH = DATA_DIR / "analytics_demo.db"

analytics_engine = create_engine(f"sqlite:///{ANALYTICS_DB_PATH}", echo=False)


def analytics_db_exists() -> bool:
    return ANALYTICS_DB_PATH.exists()
