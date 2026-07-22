from __future__ import annotations

import logging
import json
import re
import time
from dataclasses import dataclass
from typing import Iterable
from urllib.parse import quote_plus, urljoin
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

LOGGER = logging.getLogger(__name__)

CROWDWORKS_BASE_URL = "https://crowdworks.jp"
DEFAULT_USER_AGENT = "short-video-job-watcher/0.1 (+personal notification bot)"


@dataclass(frozen=True)
class Job:
    job_id: str
    title: str
    url: str
    amount_text: str
    posted_at: str
    deadline: str
    body_excerpt: str
    detected_keywords: list[str]


class RobotsBlockedError(RuntimeError):
    pass


class CrowdWorksScraper:
    def __init__(
        self,
        *,
        keywords: list[str],
        search_urls: list[str] | None = None,
        user_agent: str = DEFAULT_USER_AGENT,
        request_delay_seconds: float = 1.0,
        timeout_seconds: int = 15,
        allow_on_robots_unavailable: bool = False,
        max_detail_pages: int = 20,
    ) -> None:
        self.keywords = keywords
        self.search_urls = search_urls or self._build_default_search_urls(keywords)
        self.user_agent = user_agent
        self.request_delay_seconds = request_delay_seconds
        self.timeout_seconds = timeout_seconds
        self.allow_on_robots_unavailable = allow_on_robots_unavailable
        self.max_detail_pages = max_detail_pages
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})
        self._robots: RobotFileParser | None = None

    def fetch_jobs(self) -> list[Job]:
        candidates: dict[str, Job] = {}
        for search_url in self.search_urls:
            self._ensure_allowed(search_url)
            html = self._get(search_url)
            for job in parse_search_results(html, base_url=CROWDWORKS_BASE_URL):
                candidates[job.job_id] = job

        enriched: list[Job] = []
        for job in list(candidates.values())[: self.max_detail_pages]:
            try:
                self._ensure_allowed(job.url)
                detail_html = self._get(job.url)
                enriched.append(merge_job_detail(job, parse_job_detail(detail_html, job.url)))
            except Exception as exc:  # noqa: BLE001 - keep one bad page from stopping notifications
                LOGGER.warning("Failed to fetch detail for %s: %s", job.url, exc)
                enriched.append(job)
        return enriched

    def _build_default_search_urls(self, keywords: Iterable[str]) -> list[str]:
        urls = []
        for keyword in keywords:
            encoded = quote_plus(keyword)
            urls.append(
                f"{CROWDWORKS_BASE_URL}/public/jobs/search"
                f"?search%5Bkeywords%5D={encoded}&order=new"
            )
        return urls

    def _get(self, url: str) -> str:
        LOGGER.info("Fetching %s", url)
        response = self.session.get(url, timeout=self.timeout_seconds)
        response.raise_for_status()
        time.sleep(self.request_delay_seconds)
        return response.text

    def _ensure_allowed(self, url: str) -> None:
        robots = self._get_robots()
        if robots is None:
            if self.allow_on_robots_unavailable:
                LOGGER.warning("robots.txt unavailable; continuing because configured to allow it")
                return
            raise RobotsBlockedError("robots.txt could not be checked; refusing to fetch site pages")
        if not robots.can_fetch(self.user_agent, url):
            raise RobotsBlockedError(f"robots.txt does not allow fetching {url}")

    def _get_robots(self) -> RobotFileParser | None:
        if self._robots is not None:
            return self._robots

        robots = RobotFileParser()
        robots.set_url(f"{CROWDWORKS_BASE_URL}/robots.txt")
        try:
            robots.read()
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning("Unable to read robots.txt: %s", exc)
            return None
        self._robots = robots
        return robots


def parse_search_results(html: str, *, base_url: str) -> list[Job]:
    soup = BeautifulSoup(html, "html.parser")
    vue_jobs = parse_vue_container_jobs(soup, base_url=base_url)
    if vue_jobs:
        return vue_jobs

    jobs: dict[str, Job] = {}

    for link in soup.select('a[href*="/public/jobs/"]'):
        href = link.get("href") or ""
        job_id = extract_job_id(href)
        if not job_id:
            continue
        url = urljoin(base_url, href.split("?")[0])
        card = link.find_parent(["article", "li", "div"]) or link.parent or link
        text = normalize_space(card.get_text(" ", strip=True))
        title = normalize_space(link.get_text(" ", strip=True))
        if not title:
            continue
        jobs[job_id] = Job(
            job_id=job_id,
            title=title,
            url=url,
            amount_text=extract_amount_text(text),
            posted_at=extract_posted_at(text),
            deadline=extract_deadline(text),
            body_excerpt=truncate(text, 220),
            detected_keywords=[],
        )
    return list(jobs.values())


def parse_vue_container_jobs(soup: BeautifulSoup, *, base_url: str) -> list[Job]:
    container = soup.select_one("#vue-container")
    if not container or not container.get("data"):
        return []

    try:
        data = json.loads(container["data"])
    except json.JSONDecodeError:
        LOGGER.warning("Failed to parse vue-container data")
        return []

    search_result = data.get("searchResult") or {}
    jobs = []
    for item in search_result.get("job_offers") or []:
        job_offer = item.get("job_offer") or {}
        job_id = str(job_offer.get("id") or "")
        if not job_id:
            continue
        jobs.append(
            Job(
                job_id=job_id,
                title=normalize_space(str(job_offer.get("title") or "")),
                url=urljoin(base_url, f"/public/jobs/{job_id}"),
                amount_text=format_payment(item.get("payment") or {}),
                posted_at=format_posted_at(str(job_offer.get("last_released_at") or "")),
                deadline=format_deadline(str(job_offer.get("expired_on") or "")),
                body_excerpt=truncate(str(job_offer.get("description_digest") or ""), 300),
                detected_keywords=[],
            )
        )
    return jobs


def format_payment(payment: dict) -> str:
    fixed = payment.get("fixed_price_payment") or {}
    if fixed:
        min_budget = fixed.get("min_budget")
        max_budget = fixed.get("max_budget")
        return format_yen_range(min_budget, max_budget)

    hourly = payment.get("hourly_payment") or {}
    if hourly:
        min_wage = hourly.get("min_hourly_wage")
        max_wage = hourly.get("max_hourly_wage")
        return f"時間単価 {format_yen_range(min_wage, max_wage)}"

    return ""


def format_yen_range(min_value: object, max_value: object) -> str:
    min_yen = _to_int(min_value)
    max_yen = _to_int(max_value)
    if min_yen and max_yen and min_yen != max_yen:
        return f"{min_yen:,}円〜{max_yen:,}円"
    value = min_yen or max_yen
    return f"{value:,}円" if value else ""


def format_posted_at(value: str) -> str:
    if not value:
        return ""
    return value.replace("T", " ").replace("+09:00", "")


def format_deadline(value: str) -> str:
    if not value:
        return ""
    parts = value.split("-")
    if len(parts) == 3:
        return f"{int(parts[0])}年{int(parts[1])}月{int(parts[2])}日"
    return value


def _to_int(value: object) -> int:
    if value in (None, ""):
        return 0
    return int(float(value))


def parse_job_detail(html: str, url: str) -> dict[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    page_text = normalize_space(soup.get_text(" ", strip=True))
    title_el = soup.select_one("h1")
    body_el = (
        soup.select_one('[class*="description"]')
        or soup.select_one('[class*="detail"]')
        or soup.select_one("main")
        or soup.body
    )
    body_text = normalize_space(body_el.get_text(" ", strip=True)) if body_el else page_text
    return {
        "title": normalize_space(title_el.get_text(" ", strip=True)) if title_el else "",
        "amount_text": extract_amount_text(page_text),
        "posted_at": extract_posted_at(page_text),
        "deadline": extract_deadline(page_text),
        "body_excerpt": truncate(body_text, 300),
        "url": url,
    }


def merge_job_detail(job: Job, detail: dict[str, str]) -> Job:
    return Job(
        job_id=job.job_id,
        title=detail.get("title") or job.title,
        url=job.url,
        amount_text=detail.get("amount_text") or job.amount_text,
        posted_at=detail.get("posted_at") or job.posted_at,
        deadline=detail.get("deadline") or job.deadline,
        body_excerpt=detail.get("body_excerpt") or job.body_excerpt,
        detected_keywords=job.detected_keywords,
    )


def extract_job_id(url: str) -> str:
    match = re.search(r"/public/jobs/(\d+)", url)
    return match.group(1) if match else ""


def extract_amount_text(text: str) -> str:
    patterns = [
        r"(?:固定報酬|報酬|予算|契約金額|支払い)[^\d]{0,12}[\d,]+円(?:\s*[〜~\-－]\s*[\d,]+円)?",
        r"[\d,]+円(?:\s*[〜~\-－]\s*[\d,]+円)?",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return normalize_space(match.group(0))
    return ""


def extract_posted_at(text: str) -> str:
    patterns = [
        r"\d+\s*(?:分|時間|日)前",
        r"\d{4}年\d{1,2}月\d{1,2}日",
        r"\d{4}/\d{1,2}/\d{1,2}",
    ]
    return _first_match(patterns, text)


def extract_deadline(text: str) -> str:
    patterns = [
        r"(?:応募期限|募集期限|期限)[^\d]{0,8}\d{4}年\d{1,2}月\d{1,2}日",
        r"(?:応募期限|募集期限|期限)[^\d]{0,8}\d{4}/\d{1,2}/\d{1,2}",
        r"\d{4}年\d{1,2}月\d{1,2}日\s*まで",
    ]
    return _first_match(patterns, text)


def _first_match(patterns: Iterable[str], text: str) -> str:
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return normalize_space(match.group(0))
    return ""


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def truncate(value: str, length: int) -> str:
    value = normalize_space(value)
    if len(value) <= length:
        return value
    return value[: length - 1] + "…"
