from datetime import datetime, timedelta, timezone

import httpx
import respx

from app.crawler.arbeitnow import ArbeitnowCrawler

NOW = datetime.now(timezone.utc)


def _job(slug: str, hours_ago: float, **overrides) -> dict:
    job = {
        "slug": slug,
        "title": "Product Manager",
        "company_name": "Acme",
        "location": "Remote",
        "remote": True,
        "description": "desc",
        "url": f"https://arbeitnow.com/jobs/{slug}",
        "created_at": int((NOW - timedelta(hours=hours_ago)).timestamp()),
    }
    job.update(overrides)
    return job


@respx.mock
def test_search_jobs_filters_by_lookback_window():
    recent_job = _job("recent", hours_ago=2)
    old_job = _job("old", hours_ago=100)
    respx.get("https://www.arbeitnow.com/api/job-board-api").mock(
        return_value=httpx.Response(
            200, json={"data": [recent_job, old_job], "links": {"next": None}}
        )
    )
    crawler = ArbeitnowCrawler(lookback_hours=48)

    jobs = crawler.search_jobs()

    assert [j["slug"] for j in jobs] == ["recent"]


@respx.mock
def test_search_jobs_follows_pagination_until_cutoff():
    page1 = [_job("p1-a", hours_ago=1), _job("p1-b", hours_ago=2)]
    page2 = [_job("p2-a", hours_ago=3)]

    route = respx.get(url__regex=r"^https://www\.arbeitnow\.com/api/job-board-api").mock(
        side_effect=[
            httpx.Response(
                200,
                json={
                    "data": page1,
                    "links": {"next": "https://www.arbeitnow.com/api/job-board-api?page=2"},
                },
            ),
            httpx.Response(200, json={"data": page2, "links": {"next": None}}),
        ]
    )
    crawler = ArbeitnowCrawler(lookback_hours=48)

    jobs = crawler.search_jobs()

    assert route.call_count == 2
    assert {j["slug"] for j in jobs} == {"p1-a", "p1-b", "p2-a"}


@respx.mock
def test_search_jobs_stops_pagination_once_page_is_older_than_cutoff():
    page1 = [_job("p1-a", hours_ago=1)]
    page2_too_old = [_job("p2-a", hours_ago=200)]

    route = respx.get(url__regex=r"^https://www\.arbeitnow\.com/api/job-board-api").mock(
        side_effect=[
            httpx.Response(
                200,
                json={
                    "data": page1,
                    "links": {"next": "https://www.arbeitnow.com/api/job-board-api?page=2"},
                },
            ),
            httpx.Response(200, json={"data": page2_too_old, "links": {"next": None}}),
        ]
    )
    crawler = ArbeitnowCrawler(lookback_hours=48)

    jobs = crawler.search_jobs()

    assert route.call_count == 2
    assert [j["slug"] for j in jobs] == ["p1-a"]


def test_parse_job_builds_job_dto():
    crawler = ArbeitnowCrawler()

    dto = crawler.parse_job(_job("slug-1", hours_ago=1))

    assert dto.title == "Product Manager"
    assert dto.company == "Acme"
    assert dto.remote is True
    assert dto.source == "arbeitnow"
    assert dto.external_id == "slug-1"
