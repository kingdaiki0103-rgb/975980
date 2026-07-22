from filters import detect_keywords, filter_jobs, max_display_amount_yen
from scraper import Job


def make_job(**overrides):
    values = {
        "job_id": "123",
        "title": "TikTokショート動画編集者募集",
        "url": "https://crowdworks.jp/public/jobs/123",
        "amount_text": "固定報酬 5,000円",
        "posted_at": "10分前",
        "deadline": "応募期限 2026年8月1日",
        "body_excerpt": "縦型動画の編集をお願いします。",
        "detected_keywords": [],
    }
    values.update(overrides)
    return Job(**values)


def test_max_display_amount_yen_uses_largest_number():
    assert max_display_amount_yen("3,000円 〜 8,000円") == 8000


def test_detect_keywords_matches_title_and_body():
    job = make_job()
    assert detect_keywords(job, ["TikTok", "Instagramリール"]) == ["TikTok"]


def test_filter_jobs_requires_keyword_and_min_amount():
    jobs = [
        make_job(job_id="1", amount_text="5,000円"),
        make_job(job_id="2", title="通常動画編集", body_excerpt="動画編集", amount_text="10,000円"),
        make_job(job_id="3", amount_text="1,000円"),
    ]
    matched = filter_jobs(jobs, min_amount_yen=3000)
    assert [job.job_id for job in matched] == ["1"]
    assert matched[0].detected_keywords
