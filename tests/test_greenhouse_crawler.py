import httpx
import respx

from app.crawler.greenhouse import GreenhouseCrawler

RAW_JOB = {
    "id": 12345,
    "title": "Product Manager",
    "location": {"name": "Remote - Sweden"},
    "content": "<p>Great <b>role</b> for a PM.</p>",
    "absolute_url": "https://boards.greenhouse.io/spotify/jobs/12345",
}


@respx.mock
def test_search_jobs_returns_raw_jobs_from_api():
    respx.get("https://boards-api.greenhouse.io/v1/boards/spotify/jobs").mock(
        return_value=httpx.Response(200, json={"jobs": [RAW_JOB]})
    )
    crawler = GreenhouseCrawler(board_token="spotify")

    jobs = crawler.search_jobs()

    assert jobs == [RAW_JOB]


def test_parse_job_builds_job_dto():
    crawler = GreenhouseCrawler(board_token="spotify")

    dto = crawler.parse_job(RAW_JOB)

    assert dto.title == "Product Manager"
    assert dto.company == "spotify"
    assert dto.location == "Remote - Sweden"
    assert dto.remote is True
    assert dto.description == "Great role for a PM."
    assert dto.url == "https://boards.greenhouse.io/spotify/jobs/12345"
    assert dto.source == "greenhouse"
    assert dto.external_id == "12345"


@respx.mock
def test_collect_skips_jobs_that_fail_to_parse():
    broken_job = {"id": 999, "title": "Sem URL"}  # falta absolute_url -> KeyError no parse_job
    respx.get("https://boards-api.greenhouse.io/v1/boards/spotify/jobs").mock(
        return_value=httpx.Response(200, json={"jobs": [RAW_JOB, broken_job]})
    )
    crawler = GreenhouseCrawler(board_token="spotify")

    jobs = crawler.collect()

    assert len(jobs) == 1
    assert jobs[0].external_id == "12345"
