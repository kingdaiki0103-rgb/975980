from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from filters import TARGET_KEYWORDS, filter_jobs
from notifier import send_discord_notification
from scraper import CrowdWorksScraper, RobotsBlockedError
from storage import Storage

LOGGER = logging.getLogger(__name__)


def main() -> int:
    load_dotenv()
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        raise RuntimeError("DISCORD_WEBHOOK_URL is required")

    db_path = Path(os.getenv("DB_PATH", "data/notified_jobs.sqlite"))
    min_amount_yen = int(os.getenv("MIN_AMOUNT_YEN", "3000"))
    dry_run = os.getenv("DRY_RUN", "false").lower() == "true"
    search_urls = _split_env("CROWDWORKS_SEARCH_URLS")

    scraper = CrowdWorksScraper(
        keywords=TARGET_KEYWORDS,
        search_urls=search_urls or None,
        request_delay_seconds=float(os.getenv("REQUEST_DELAY_SECONDS", "1.0")),
        timeout_seconds=int(os.getenv("REQUEST_TIMEOUT_SECONDS", "15")),
        allow_on_robots_unavailable=os.getenv("ALLOW_ON_ROBOTS_UNAVAILABLE", "false").lower()
        == "true",
        max_detail_pages=int(os.getenv("MAX_DETAIL_PAGES", "20")),
    )
    storage = Storage(db_path)

    try:
        jobs = scraper.fetch_jobs()
    except RobotsBlockedError as exc:
        LOGGER.error("Stopped for robots.txt safety: %s", exc)
        return 2

    matched_jobs = filter_jobs(jobs, min_amount_yen=min_amount_yen)
    new_jobs = [job for job in matched_jobs if not storage.already_notified(job)]

    LOGGER.info("Fetched=%d matched=%d new=%d", len(jobs), len(matched_jobs), len(new_jobs))
    for job in new_jobs:
        if dry_run:
            LOGGER.info("[DRY_RUN] Would notify: %s %s", job.title, job.url)
        else:
            send_discord_notification(webhook_url, job)
        storage.mark_notified(job)

    return 0


def _split_env(name: str) -> list[str]:
    value = os.getenv(name, "")
    return [item.strip() for item in value.split(",") if item.strip()]


if __name__ == "__main__":
    raise SystemExit(main())
