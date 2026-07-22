from __future__ import annotations

import re

from scraper import Job

TARGET_KEYWORDS = [
    "ショート動画",
    "ショート動画編集",
    "TikTok",
    "TikTok編集",
    "リール動画",
    "Instagramリール",
    "YouTube Shorts",
    "縦型動画",
    "SNS動画編集",
]

VIDEO_EDITING_HINTS = ["動画編集", "編集者", "動画", "映像編集", "TikTok", "リール", "Shorts", "縦型"]


def filter_jobs(
    jobs: list[Job],
    *,
    min_amount_yen: int = 3000,
    target_keywords: list[str] | None = None,
) -> list[Job]:
    keywords = target_keywords or TARGET_KEYWORDS
    matched: list[Job] = []
    for job in jobs:
        detected = detect_keywords(job, keywords)
        if not detected:
            continue
        if not looks_like_video_editing(job):
            continue
        if max_display_amount_yen(job.amount_text) < min_amount_yen:
            continue
        matched.append(
            Job(
                job_id=job.job_id,
                title=job.title,
                url=job.url,
                amount_text=job.amount_text,
                posted_at=job.posted_at,
                deadline=job.deadline,
                body_excerpt=job.body_excerpt,
                detected_keywords=detected,
            )
        )
    return matched


def detect_keywords(job: Job, keywords: list[str]) -> list[str]:
    haystack = f"{job.title} {job.body_excerpt}".casefold()
    return [keyword for keyword in keywords if keyword.casefold() in haystack]


def looks_like_video_editing(job: Job) -> bool:
    haystack = f"{job.title} {job.body_excerpt}".casefold()
    return any(hint.casefold() in haystack for hint in VIDEO_EDITING_HINTS)


def max_display_amount_yen(amount_text: str) -> int:
    numbers = [int(value.replace(",", "")) for value in re.findall(r"\d[\d,]*", amount_text)]
    return max(numbers, default=0)
