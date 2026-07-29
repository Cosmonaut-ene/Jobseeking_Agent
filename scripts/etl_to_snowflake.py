"""ETL: data/analytics_demo.db -> Snowflake star schema (TASK-D04, SPEC.md 附录 E.8).

Reads the synthetic analytics_demo.db (see scripts/generate_analytics_demo_data.py)
and loads it into a dimensional model in Snowflake: dim_date, dim_company,
dim_job, fact_application.

Credentials come only from environment variables (see .env.example's
Snowflake section) — never hardcoded, never committed. Safe to re-run: all
tables are CREATE OR REPLACE.

Usage:
    PYTHONPATH=. python3 scripts/etl_to_snowflake.py
"""
import os
import sqlite3
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

from backend.app.config import DATA_DIR

load_dotenv()

ANALYTICS_DB_PATH = DATA_DIR / "analytics_demo.db"

REQUIRED_ENV_VARS = [
    "SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER", "SNOWFLAKE_PASSWORD",
    "SNOWFLAKE_WAREHOUSE", "SNOWFLAKE_DATABASE", "SNOWFLAKE_SCHEMA",
]

DDL_TEMPLATE = """
CREATE DATABASE IF NOT EXISTS {database};
CREATE SCHEMA IF NOT EXISTS {database}.{schema};

CREATE OR REPLACE TABLE {database}.{schema}.dim_date (
    date_key INTEGER PRIMARY KEY,
    full_date DATE,
    year INTEGER,
    month INTEGER,
    day INTEGER,
    day_of_week VARCHAR(9),
    week_of_year INTEGER
);

CREATE OR REPLACE TABLE {database}.{schema}.dim_company (
    company_key INTEGER PRIMARY KEY,
    company_name VARCHAR,
    industry VARCHAR
);

CREATE OR REPLACE TABLE {database}.{schema}.dim_job (
    job_key VARCHAR PRIMARY KEY,
    title VARCHAR,
    source VARCHAR,
    location VARCHAR,
    salary_min INTEGER,
    salary_max INTEGER
);

CREATE OR REPLACE TABLE {database}.{schema}.fact_application (
    application_key VARCHAR PRIMARY KEY,
    job_key VARCHAR,
    company_key INTEGER,
    applied_date_key INTEGER,
    match_score FLOAT,
    final_status VARCHAR,
    channel VARCHAR,
    days_to_first_response INTEGER
);
"""

VERIFICATION_SQL = """
SELECT
    c.industry,
    COUNT(*) AS applications,
    ROUND(AVG(f.match_score), 2) AS avg_match_score,
    ROUND(AVG(f.days_to_first_response), 1) AS avg_days_to_first_response
FROM fact_application f
JOIN dim_company c ON c.company_key = f.company_key
GROUP BY c.industry
ORDER BY applications DESC
"""


def _require_env() -> dict[str, str]:
    missing = [v for v in REQUIRED_ENV_VARS if not os.environ.get(v)]
    if missing:
        raise SystemExit(
            f"Missing required env vars: {', '.join(missing)}. "
            "Copy the Snowflake section from .env.example into .env and fill in real values."
        )
    return {v: os.environ[v] for v in REQUIRED_ENV_VARS}


def _date_key(d: date) -> int:
    return int(d.strftime("%Y%m%d"))


def _build_dim_date(min_date: date, max_date: date) -> list[tuple]:
    rows = []
    d = min_date
    while d <= max_date:
        rows.append((_date_key(d), d.isoformat(), d.year, d.month, d.day, d.strftime("%A"), int(d.strftime("%W"))))
        d += timedelta(days=1)
    return rows


def extract() -> dict:
    if not ANALYTICS_DB_PATH.exists():
        raise SystemExit(
            f"{ANALYTICS_DB_PATH} not found. Run "
            "`PYTHONPATH=. python3 scripts/generate_analytics_demo_data.py` first."
        )
    conn = sqlite3.connect(ANALYTICS_DB_PATH)
    conn.row_factory = sqlite3.Row
    data = {
        "companies": conn.execute("SELECT id, name, industry FROM demo_company").fetchall(),
        "jobs": conn.execute(
            "SELECT id, title, source, location, salary_min, salary_max, "
            "match_score, status, created_at, company_id FROM demo_job"
        ).fetchall(),
        "applications": conn.execute("SELECT id, job_id, channel, applied_at FROM demo_application").fetchall(),
        "status_logs": conn.execute(
            "SELECT application_id, status, changed_at FROM demo_application_status_log "
            "ORDER BY application_id, changed_at"
        ).fetchall(),
    }
    conn.close()
    return data


def transform(data: dict) -> dict:
    jobs_by_id = {j["id"]: j for j in data["jobs"]}

    logs_by_app: dict[str, list] = {}
    for row in data["status_logs"]:
        logs_by_app.setdefault(row["application_id"], []).append(row)

    def _days_to_first_response(app_id: str) -> int | None:
        # Gap between the "submitted" entry and the next status change — the
        # first real movement on the application after it went in.
        entries = logs_by_app.get(app_id, [])
        if len(entries) < 2:
            return None
        first = datetime.fromisoformat(entries[0]["changed_at"])
        second = datetime.fromisoformat(entries[1]["changed_at"])
        return (second - first).days

    dim_company_rows = [(c["id"], c["name"], c["industry"]) for c in data["companies"]]
    dim_job_rows = [
        (j["id"], j["title"], j["source"], j["location"], j["salary_min"], j["salary_max"])
        for j in data["jobs"]
    ]

    all_dates = [datetime.fromisoformat(j["created_at"]).date() for j in data["jobs"]]
    all_dates += [datetime.fromisoformat(a["applied_at"]).date() for a in data["applications"]]
    dim_date_rows = _build_dim_date(min(all_dates), max(all_dates))

    fact_rows = []
    for a in data["applications"]:
        job = jobs_by_id.get(a["job_id"])
        if job is None:
            continue
        applied_date = datetime.fromisoformat(a["applied_at"]).date()
        fact_rows.append((
            a["id"], a["job_id"], job["company_id"], _date_key(applied_date),
            job["match_score"], job["status"], a["channel"], _days_to_first_response(a["id"]),
        ))

    return {
        "dim_date": dim_date_rows,
        "dim_company": dim_company_rows,
        "dim_job": dim_job_rows,
        "fact_application": fact_rows,
    }


def load(rows: dict, creds: dict) -> list[tuple]:
    import snowflake.connector

    conn = snowflake.connector.connect(
        account=creds["SNOWFLAKE_ACCOUNT"],
        user=creds["SNOWFLAKE_USER"],
        password=creds["SNOWFLAKE_PASSWORD"],
        warehouse=creds["SNOWFLAKE_WAREHOUSE"],
    )
    database = creds["SNOWFLAKE_DATABASE"]
    schema = creds["SNOWFLAKE_SCHEMA"]
    cur = conn.cursor()
    try:
        for statement in DDL_TEMPLATE.format(database=database, schema=schema).split(";"):
            statement = statement.strip()
            if statement:
                cur.execute(statement)

        cur.execute(f"USE DATABASE {database}")
        cur.execute(f"USE SCHEMA {schema}")

        cur.executemany(
            "INSERT INTO dim_date (date_key, full_date, year, month, day, day_of_week, week_of_year) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            rows["dim_date"],
        )
        cur.executemany(
            "INSERT INTO dim_company (company_key, company_name, industry) VALUES (%s, %s, %s)",
            rows["dim_company"],
        )
        cur.executemany(
            "INSERT INTO dim_job (job_key, title, source, location, salary_min, salary_max) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            rows["dim_job"],
        )
        cur.executemany(
            "INSERT INTO fact_application "
            "(application_key, job_key, company_key, applied_date_key, match_score, "
            " final_status, channel, days_to_first_response) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            rows["fact_application"],
        )
        conn.commit()

        print("Loaded into Snowflake:")
        for table in ("dim_date", "dim_company", "dim_job", "fact_application"):
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            print(f"  {table}: {cur.fetchone()[0]} rows")

        cur.execute(VERIFICATION_SQL)
        verification_rows = cur.fetchall()
        verification_columns = [c[0] for c in cur.description]
        return [tuple(verification_columns)] + verification_rows
    finally:
        cur.close()
        conn.close()


def main() -> None:
    creds = _require_env()
    data = extract()
    star_schema_rows = transform(data)
    verification_result = load(star_schema_rows, creds)

    print("\nVerification query — avg match_score / days_to_first_response by industry:")
    for row in verification_result:
        print("  ", row)

    out_dir = Path(__file__).resolve().parents[1] / "docs" / "snowflake_verification"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"verification_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with out_path.open("w") as f:
        f.write("Verification query: avg match_score / days_to_first_response by industry\n")
        f.write(VERIFICATION_SQL + "\n\n")
        for row in verification_result:
            f.write(str(row) + "\n")
    print(f"\nSaved verification output to {out_path}")


if __name__ == "__main__":
    main()
