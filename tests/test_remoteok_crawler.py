from datetime import datetime, timedelta, timezone

import httpx
import respx

from app.crawler.remoteok import RemoteOKCrawler

NOW = datetime.now(timezone.utc)
LEGAL_NOTICE = {"legal": "https://remoteok.com/legal", "api": "https://remoteok.com/api"}


def _job(job_id: int, hours_ago: float, **overrides) -> dict:
    job = {
        "id": job_id,
        "position": "Product Manager",
        "company": "Acme",
        "location": "Worldwide",
        "description": "<p>Great <b>role</b></p>",
        "url": f"https://remoteok.com/remote-jobs/{job_id}",
        "epoch": int((NOW - timedelta(hours=hours_ago)).timestamp()),
    }
    job.update(overrides)
    return job


@respx.mock
def test_search_jobs_skips_legal_notice_and_filters_by_lookback():
    recent = _job(1, hours_ago=2)
    old = _job(2, hours_ago=100)
    respx.get("https://remoteok.com/api").mock(
        return_value=httpx.Response(200, json=[LEGAL_NOTICE, recent, old])
    )
    crawler = RemoteOKCrawler(lookback_hours=48)

    jobs = crawler.search_jobs()

    assert [j["id"] for j in jobs] == [1]


def test_parse_job_builds_job_dto_with_apply_url_precedence():
    crawler = RemoteOKCrawler()
    raw = _job(1, hours_ago=1, apply_url="https://acme.com/apply/1")

    dto = crawler.parse_job(raw)

    assert dto.title == "Product Manager"
    assert dto.company == "Acme"
    assert dto.remote is True
    assert dto.description == "Great role"
    assert dto.url == "https://acme.com/apply/1"
    assert dto.source == "remoteok"
    assert dto.external_id == "1"


def test_parse_job_falls_back_to_url_when_no_apply_url():
    crawler = RemoteOKCrawler()
    raw = _job(2, hours_ago=1)

    dto = crawler.parse_job(raw)

    assert dto.url == "https://remoteok.com/remote-jobs/2"
