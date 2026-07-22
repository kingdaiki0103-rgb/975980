from scraper import extract_job_id, parse_job_detail, parse_search_results


def test_parse_search_results_extracts_public_jobs():
    html = """
    <html><body>
      <article>
        <a href="/public/jobs/123456">TikTokショート動画編集者募集</a>
        <span>固定報酬 5,000円</span>
        <span>10分前</span>
        <span>応募期限 2026年8月1日</span>
      </article>
    </body></html>
    """
    jobs = parse_search_results(html, base_url="https://crowdworks.jp")
    assert len(jobs) == 1
    assert jobs[0].job_id == "123456"
    assert jobs[0].amount_text == "固定報酬 5,000円"
    assert jobs[0].posted_at == "10分前"


def test_parse_job_detail_extracts_h1_and_body():
    html = """
    <html><body>
      <h1>Instagramリール動画の編集</h1>
      <main>
        報酬 7,000円 掲載日 2026年7月23日 応募期限 2026年8月10日
        SNS動画編集の経験者を募集します。
      </main>
    </body></html>
    """
    detail = parse_job_detail(html, "https://crowdworks.jp/public/jobs/999")
    assert detail["title"] == "Instagramリール動画の編集"
    assert detail["amount_text"] == "報酬 7,000円"
    assert "SNS動画編集" in detail["body_excerpt"]


def test_extract_job_id_rejects_non_job_url():
    assert extract_job_id("/public/jobs/123") == "123"
    assert extract_job_id("/users/123") == ""
