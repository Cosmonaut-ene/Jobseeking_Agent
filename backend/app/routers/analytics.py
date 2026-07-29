"""Analytics router — raw SQL over the synthetic data/analytics_demo.db (TASK-D02).

Deliberately uses session.exec(text(...)) rather than the SQLModel query
builder (select()/func): the point of this module is to demonstrate
hand-written SQL (conditional aggregation, JOINs, CTEs, window functions,
JSON extraction), not to hide it behind an ORM. Read-only — no
INSERT/UPDATE/DELETE anywhere in this file.
"""
from fastapi import APIRouter, HTTPException, Query
from sqlmodel import Session, text

from backend.app.analytics_db import analytics_db_exists, analytics_engine

router = APIRouter(prefix="/analytics", tags=["analytics"])

_MISSING_DB_DETAIL = (
    "analytics_demo.db not found. Run "
    "`PYTHONPATH=. python3 scripts/generate_analytics_demo_data.py` first."
)


def _analytics_session() -> Session:
    if not analytics_db_exists():
        raise HTTPException(404, detail=_MISSING_DB_DETAIL)
    return Session(analytics_engine)


def _rows_to_dicts(rows) -> list[dict]:
    return [dict(row._mapping) for row in rows]


@router.get("/funnel")
def get_funnel() -> list[dict]:
    """Source x status conversion matrix via conditional aggregation."""
    sql = text("""
        SELECT
            source,
            SUM(CASE WHEN status = 'new'       THEN 1 ELSE 0 END) AS new,
            SUM(CASE WHEN status = 'reviewed'  THEN 1 ELSE 0 END) AS reviewed,
            SUM(CASE WHEN status = 'dismissed' THEN 1 ELSE 0 END) AS dismissed,
            SUM(CASE WHEN status = 'applied'   THEN 1 ELSE 0 END) AS applied,
            SUM(CASE WHEN status = 'interview' THEN 1 ELSE 0 END) AS interview,
            SUM(CASE WHEN status = 'rejected'  THEN 1 ELSE 0 END) AS rejected,
            SUM(CASE WHEN status = 'offer'     THEN 1 ELSE 0 END) AS offer,
            COUNT(*) AS total
        FROM demo_job
        GROUP BY source
        ORDER BY total DESC
    """)
    with _analytics_session() as session:
        return _rows_to_dicts(session.exec(sql).all())


@router.get("/skill-gaps")
def get_skill_gaps(limit: int = Query(10, ge=1, le=50)) -> list[dict]:
    """Top N missing skills, extracted from the gap_analysis JSON column via json_each()."""
    sql = text("""
        SELECT je.value AS skill, COUNT(*) AS count
        FROM demo_job j, json_each(j.gap_analysis_json, '$.missing_skills') je
        GROUP BY je.value
        ORDER BY count DESC
        LIMIT :limit
    """)
    with _analytics_session() as session:
        return _rows_to_dicts(session.exec(sql, params={"limit": limit}).all())


@router.get("/score-distribution")
def get_score_distribution() -> dict:
    """Match-score histogram (10% buckets) plus per-source summary stats."""
    histogram_sql = text("""
        SELECT
            CAST(match_score * 10 AS INT) * 10 AS bucket_start,
            COUNT(*) AS count
        FROM demo_job
        GROUP BY bucket_start
        ORDER BY bucket_start
    """)
    by_source_sql = text("""
        SELECT
            source,
            COUNT(*) AS count,
            ROUND(AVG(match_score), 2) AS avg_score,
            ROUND(MIN(match_score), 2) AS min_score,
            ROUND(MAX(match_score), 2) AS max_score
        FROM demo_job
        GROUP BY source
        ORDER BY avg_score DESC
    """)
    with _analytics_session() as session:
        histogram = _rows_to_dicts(session.exec(histogram_sql).all())
        by_source = _rows_to_dicts(session.exec(by_source_sql).all())
    return {"histogram": histogram, "by_source": by_source}


@router.get("/discovery-trend")
def get_discovery_trend() -> list[dict]:
    """Jobs discovered per day, with a 7-day moving average window function."""
    sql = text("""
        WITH daily AS (
            SELECT DATE(created_at) AS day, COUNT(*) AS jobs_found
            FROM demo_job
            GROUP BY DATE(created_at)
        )
        SELECT
            day,
            jobs_found,
            ROUND(
                AVG(jobs_found) OVER (ORDER BY day ROWS BETWEEN 6 PRECEDING AND CURRENT ROW),
                1
            ) AS moving_avg_7d
        FROM daily
        ORDER BY day
    """)
    with _analytics_session() as session:
        return _rows_to_dicts(session.exec(sql).all())


@router.get("/conversion")
def get_conversion() -> list[dict]:
    """Application conversion rate by match-score bucket (CTE + LEFT JOIN)."""
    sql = text("""
        WITH scored AS (
            SELECT
                id,
                CASE
                    WHEN match_score >= 0.8 THEN 3
                    WHEN match_score >= 0.6 THEN 2
                    WHEN match_score >= 0.4 THEN 1
                    ELSE 0
                END AS bucket_order,
                CASE
                    WHEN match_score >= 0.8 THEN '80-100%'
                    WHEN match_score >= 0.6 THEN '60-79%'
                    WHEN match_score >= 0.4 THEN '40-59%'
                    ELSE '0-39%'
                END AS score_bucket
            FROM demo_job
        )
        SELECT
            s.score_bucket,
            COUNT(DISTINCT s.id) AS total_jobs,
            COUNT(DISTINCT a.id) AS applications,
            ROUND(CAST(COUNT(DISTINCT a.id) AS REAL) / COUNT(DISTINCT s.id) * 100, 1) AS conversion_pct
        FROM scored s
        LEFT JOIN demo_application a ON a.job_id = s.id
        GROUP BY s.score_bucket, s.bucket_order
        ORDER BY s.bucket_order DESC
    """)
    with _analytics_session() as session:
        return _rows_to_dicts(session.exec(sql).all())


@router.get("/top-companies")
def get_top_companies(limit: int = Query(10, ge=1, le=50)) -> list[dict]:
    """Most frequently seen companies (JOIN + GROUP BY + ORDER BY COUNT)."""
    sql = text("""
        SELECT
            c.name AS company,
            c.industry AS industry,
            COUNT(*) AS job_count,
            ROUND(AVG(j.match_score), 2) AS avg_match_score
        FROM demo_job j
        JOIN demo_company c ON c.id = j.company_id
        GROUP BY c.id, c.name, c.industry
        ORDER BY job_count DESC
        LIMIT :limit
    """)
    with _analytics_session() as session:
        return _rows_to_dicts(session.exec(sql, params={"limit": limit}).all())
