from __future__ import annotations

import requests

from scraper import Job


def send_discord_notification(webhook_url: str, job: Job, *, timeout_seconds: int = 15) -> None:
    payload = build_discord_payload(job)
    response = requests.post(webhook_url, json=payload, timeout=timeout_seconds)
    response.raise_for_status()


def build_discord_payload(job: Job) -> dict:
    keywords = ", ".join(job.detected_keywords) if job.detected_keywords else "未検出"
    return {
        "username": "CrowdWorks Watcher",
        "embeds": [
            {
                "title": "🚨 新着ショート動画案件",
                "description": f"**{job.title}**",
                "url": job.url,
                "color": 15158332,
                "fields": [
                    {"name": "報酬", "value": job.amount_text or "不明", "inline": True},
                    {"name": "掲載", "value": job.posted_at or "不明", "inline": True},
                    {"name": "応募期限", "value": job.deadline or "不明", "inline": True},
                    {"name": "検出したキーワード", "value": keywords, "inline": False},
                    {"name": "案件本文の冒頭", "value": job.body_excerpt or "本文を取得できませんでした", "inline": False},
                    {"name": "案件を見る", "value": job.url, "inline": False},
                ],
            }
        ],
    }
