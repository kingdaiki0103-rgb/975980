from scraper import Job
from storage import Storage


def test_storage_prevents_duplicate_notifications(tmp_path):
    storage = Storage(tmp_path / "jobs.sqlite")
    job = Job(
        job_id="123",
        title="TikTok編集",
        url="https://crowdworks.jp/public/jobs/123",
        amount_text="5,000円",
        posted_at="5分前",
        deadline="2026年8月1日",
        body_excerpt="本文",
        detected_keywords=["TikTok"],
    )
    assert not storage.already_notified(job)
    storage.mark_notified(job)
    assert storage.already_notified(job)
