from notifier import build_discord_payload
from scraper import Job


def test_build_discord_payload_uses_embed_fields():
    job = Job(
        job_id="123",
        title="TikTokショート動画編集者募集",
        url="https://crowdworks.jp/public/jobs/123",
        amount_text="5,000円",
        posted_at="5分前",
        deadline="2026年8月1日",
        body_excerpt="冒頭本文",
        detected_keywords=["TikTok", "ショート動画"],
    )
    payload = build_discord_payload(job)
    embed = payload["embeds"][0]
    assert embed["title"] == "🚨 新着ショート動画案件"
    assert embed["url"] == job.url
    assert any(field["name"] == "案件本文の冒頭" for field in embed["fields"])
