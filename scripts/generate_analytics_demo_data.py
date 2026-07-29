"""Generate synthetic demo data for the Analytics dashboard (TASK-D01, see SPEC.md 附录 E.8).

Writes to data/analytics_demo.db — a file completely separate from the
production data/db/jobseeking.db. Safe to re-run: drops and recreates only
its own four tables, never touches the production database.
"""
import json
import random
import sqlite3
from datetime import datetime, timedelta, timezone

from faker import Faker

from backend.app.config import DATA_DIR

DB_PATH = DATA_DIR / "analytics_demo.db"

NUM_COMPANIES = 250
NUM_JOBS = 1200
NUM_APPLICATIONS = 350

SOURCES = ["seek", "linkedin", "manual"]
SOURCE_WEIGHTS = [0.45, 0.40, 0.15]

INDUSTRIES = [
    "Technology", "Finance", "Healthcare", "Retail", "Manufacturing",
    "Education", "Hospitality", "Government", "Media", "Logistics",
]

TITLES = [
    "Data Engineer", "Associate Data Engineer", "Data Analyst", "Business Intelligence Analyst",
    "Backend Engineer", "Software Engineer", "Data Scientist", "Analytics Engineer",
    "Machine Learning Engineer", "Platform Engineer", "DevOps Engineer", "Full Stack Developer",
    "ETL Developer", "Cloud Engineer", "Database Administrator",
]

LOCATIONS = ["Sydney NSW", "Melbourne VIC", "Brisbane QLD", "Remote", "Perth WA", "Canberra ACT"]

SKILLS_POOL = [
    "SQL", "Python", "AWS", "Azure", "GCP", "Docker", "Kubernetes", "Airflow",
    "Spark", "dbt", "Snowflake", "Tableau", "Power BI", "Git", "CI/CD",
    "REST API", "Postgres", "MongoDB", "Terraform", "Kafka",
]

# Mirrors backend/app/models/job.py JobStatus, weighted to resemble a realistic funnel.
STATUS_WEIGHTS = {
    "new": 0.35,
    "reviewed": 0.20,
    "dismissed": 0.15,
    "applied": 0.15,
    "interview": 0.08,
    "rejected": 0.05,
    "offer": 0.02,
}

APPLICATION_CHANNELS = ["email", "easy_apply", "manual"]

# Status-log progression per final Job.status — independent of JobStatus vocabulary
# (this table only exists in the demo warehouse layer). Always 2-4 steps so
# "days to first response" is always computable from at least two timestamps.
STATUS_PROGRESSION = {
    "applied": ["submitted", "under_review"],
    "interview": ["submitted", "under_review", "interview"],
    "rejected": ["submitted", "under_review", "rejected"],
    "offer": ["submitted", "under_review", "interview", "offer"],
}

fake = Faker()
Faker.seed(42)
random.seed(42)


def _rand_past_date(days_back_max: int) -> datetime:
    days = random.randint(0, days_back_max)
    return datetime.now(timezone.utc) - timedelta(days=days, hours=random.randint(0, 23))


def _gap_analysis_json(strong: list[str], missing: list[str], ats_pct: int) -> str:
    # Same top-level keys as the real Job.gap_analysis so json_each() queries
    # written against this demo data apply unchanged to production data.
    return json.dumps({
        "ats_pct": ats_pct,
        "strong_matches": strong,
        "missing_skills": missing,
        "unmet_requirements": [],
        "notes": "Synthetic evaluation generated for analytics demo purposes.",
    })


def _weighted_status() -> str:
    return random.choices(list(STATUS_WEIGHTS), weights=list(STATUS_WEIGHTS.values()), k=1)[0]


def create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        DROP TABLE IF EXISTS demo_application_status_log;
        DROP TABLE IF EXISTS demo_application;
        DROP TABLE IF EXISTS demo_job;
        DROP TABLE IF EXISTS demo_company;

        CREATE TABLE demo_company (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            industry TEXT NOT NULL
        );

        CREATE TABLE demo_job (
            id TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            title TEXT NOT NULL,
            company_id INTEGER NOT NULL REFERENCES demo_company(id),
            location TEXT NOT NULL,
            salary_min INTEGER NOT NULL,
            salary_max INTEGER NOT NULL,
            match_score REAL NOT NULL,
            gap_analysis_json TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE demo_application (
            id TEXT PRIMARY KEY,
            job_id TEXT NOT NULL REFERENCES demo_job(id),
            channel TEXT NOT NULL,
            applied_at TEXT NOT NULL
        );

        CREATE TABLE demo_application_status_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            application_id TEXT NOT NULL REFERENCES demo_application(id),
            status TEXT NOT NULL,
            changed_at TEXT NOT NULL
        );
        """
    )


def generate_companies(conn: sqlite3.Connection) -> None:
    rows = [(i, fake.unique.company(), random.choice(INDUSTRIES)) for i in range(1, NUM_COMPANIES + 1)]
    conn.executemany("INSERT INTO demo_company (id, name, industry) VALUES (?, ?, ?)", rows)


def generate_jobs(conn: sqlite3.Connection) -> list[tuple[str, str, datetime]]:
    """Returns (job_id, status, created_at) for jobs eligible to carry an Application."""
    rows = []
    eligible: list[tuple[str, str, datetime]] = []

    for _ in range(NUM_JOBS):
        job_id = fake.uuid4()
        source = random.choices(SOURCES, weights=SOURCE_WEIGHTS, k=1)[0]
        title = random.choice(TITLES)
        company_id = random.randint(1, NUM_COMPANIES)
        location = random.choice(LOCATIONS)
        salary_min = random.choice([90000, 100000, 110000, 120000, 130000])
        salary_max = salary_min + random.choice([15000, 20000, 25000, 30000])
        match_score = round(min(max(random.gauss(0.62, 0.18), 0.05), 0.98), 2)

        shuffled_skills = SKILLS_POOL.copy()
        random.shuffle(shuffled_skills)
        num_strong = random.randint(2, 6)
        num_missing = random.randint(1, 5)
        strong = shuffled_skills[:num_strong]
        missing = shuffled_skills[num_strong:num_strong + num_missing]

        status = _weighted_status()
        created_at = _rand_past_date(180)

        rows.append((
            job_id, source, title, company_id, location, salary_min, salary_max,
            match_score, _gap_analysis_json(strong, missing, int(match_score * 100)), status,
            created_at.isoformat(),
        ))

        if status in STATUS_PROGRESSION:
            eligible.append((job_id, status, created_at))

    conn.executemany(
        """INSERT INTO demo_job
           (id, source, title, company_id, location, salary_min, salary_max,
            match_score, gap_analysis_json, status, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        rows,
    )
    return eligible


def generate_applications(conn: sqlite3.Connection, eligible_jobs: list[tuple[str, str, datetime]]) -> None:
    sample = random.sample(eligible_jobs, k=min(NUM_APPLICATIONS, len(eligible_jobs)))
    app_rows = []
    log_rows = []

    for job_id, final_status, created_at in sample:
        app_id = fake.uuid4()
        applied_at = created_at + timedelta(days=random.randint(0, 5))
        channel = random.choice(APPLICATION_CHANNELS)
        app_rows.append((app_id, job_id, channel, applied_at.isoformat()))

        changed_at = applied_at
        for i, step in enumerate(STATUS_PROGRESSION[final_status]):
            ts = applied_at if i == 0 else changed_at + timedelta(days=random.randint(1, 10))
            log_rows.append((app_id, step, ts.isoformat()))
            changed_at = ts

    conn.executemany(
        "INSERT INTO demo_application (id, job_id, channel, applied_at) VALUES (?, ?, ?, ?)",
        app_rows,
    )
    conn.executemany(
        "INSERT INTO demo_application_status_log (application_id, status, changed_at) VALUES (?, ?, ?)",
        log_rows,
    )


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        create_schema(conn)
        generate_companies(conn)
        eligible = generate_jobs(conn)
        generate_applications(conn, eligible)
        conn.commit()
    finally:
        conn.close()

    with sqlite3.connect(DB_PATH) as verify_conn:
        counts = {
            table: verify_conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("demo_company", "demo_job", "demo_application", "demo_application_status_log")
        }
    print(f"Generated {DB_PATH}")
    for table, count in counts.items():
        print(f"  {table}: {count} rows")


if __name__ == "__main__":
    main()
