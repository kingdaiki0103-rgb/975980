from __future__ import annotations

import sqlite3
from pathlib import Path

from scraper import Job


class Storage:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def already_notified(self, job: Job) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT 1 FROM notified_jobs WHERE job_id = ? OR url = ? LIMIT 1",
                (job.job_id, job.url),
            ).fetchone()
        return row is not None

    def mark_notified(self, job: Job) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO notified_jobs
                    (job_id, url, title, amount_text, posted_at, deadline)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (job.job_id, job.url, job.title, job.amount_text, job.posted_at, job.deadline),
            )

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS notified_jobs (
                    job_id TEXT PRIMARY KEY,
                    url TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    amount_text TEXT,
                    posted_at TEXT,
                    deadline TEXT,
                    notified_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
