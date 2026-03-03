#!/usr/bin/env python3
"""
Daily scout script — triggered by OpenClaw cron or run manually.

Usage:
  python scripts/daily_scout.py              # run with settings from data/settings.json
  python scripts/daily_scout.py --run-now    # alias for above
  python scripts/daily_scout.py --dry-run    # show config, don't scrape

OpenClaw cron config:
  {
    "name": "daily-job-scout",
    "schedule": "0 9 * * *",
    "command": "python scripts/daily_scout.py",
    "enabled": true
  }
"""

import argparse
import json
import logging
import sys
from pathlib import Path

# Make backend importable from project root
sys.path.insert(0, str(Path(__file__).parents[1]))

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("daily_scout")


def load_settings() -> dict:
    settings_file = Path("data/settings.json")
    if settings_file.exists():
        data = json.loads(settings_file.read_text(encoding="utf-8"))
        return data.get("scraper_config", {})
    return {}


def dry_run(settings: dict) -> None:
    import os
    from backend.app.config import (
        GEMINI_API_KEY, NOTIFICATION_WEBHOOK_URL,
        HIGH_SCORE_THRESHOLD, MID_SCORE_THRESHOLD,
        SCHEDULER_HOUR, SCHEDULER_MINUTE,
    )
    from backend.app.scrapers.linkedin import LinkedInAutoScraper

    print("\n=== Daily Scout — Dry Run ===")
    print(f"GEMINI_API_KEY:       {'SET' if GEMINI_API_KEY else 'NOT SET ❌'}")
    print(f"NOTIFICATION_WEBHOOK: {'SET' if NOTIFICATION_WEBHOOK_URL else 'NOT SET (no push)'}")
    print(f"Schedule:             {SCHEDULER_HOUR:02d}:{SCHEDULER_MINUTE:02d} AEDT")
    print(f"High score threshold: {HIGH_SCORE_THRESHOLD:.0%}")
    print(f"Mid score threshold:  {MID_SCORE_THRESHOLD:.0%}")

    li = LinkedInAutoScraper()
    print(f"LinkedIn cookies:     {'Loaded ✅' if li.has_cookies else 'Not found (auto-skip)'}")

    try:
        from backend.app.models.user_profile import UserProfile
        profile = UserProfile.load()
        print(f"User profile:         {profile.name} — {len(profile.target_roles)} target roles")
        print(f"Target roles:         {', '.join(profile.target_roles)}")
        print(f"Locations:            {', '.join(profile.preferences.locations)}")
    except FileNotFoundError:
        print("User profile:         NOT FOUND ❌")

    if settings:
        print(f"Custom settings:      {settings}")

    print("\nRun without --dry-run to execute the scout.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Jobseeking Agent — Daily Scout")
    parser.add_argument("--dry-run", action="store_true", help="Show config without scraping")
    parser.add_argument("--run-now", action="store_true", help="Run immediately (default behavior)")
    args = parser.parse_args()

    settings = load_settings()

    if args.dry_run:
        dry_run(settings)
        return

    logger.info("=== Starting daily scout ===")

    try:
        from backend.app.database import init_db
        init_db()
        logger.info("Database initialised")
    except Exception as e:
        logger.error("Failed to init database: %s", e)
        sys.exit(1)

    try:
        from backend.app.scrapers.scheduler import run_daily_scout
        result = run_daily_scout(settings)
        logger.info("Daily scout complete: %s", result)

        print("\n=== Results ===")
        if "error" in result:
            print(f"ERROR: {result['error']}")
            sys.exit(1)
        scraped = result.get("scraped", {})
        print(f"Scraped:  Seek={scraped.get('seek', 0)}, Indeed={scraped.get('indeed', 0)}, LinkedIn={scraped.get('linkedin', 0)}")
        print(f"Saved:    {result.get('saved', 0)} jobs (high={result.get('high_score', 0)}, mid={result.get('mid_score', 0)})")

    except Exception as e:
        logger.error("Daily scout failed: %s", e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
