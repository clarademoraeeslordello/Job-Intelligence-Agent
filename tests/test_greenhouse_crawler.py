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


def _mock_metadata(name: str = "Spotify"):
    return respx.get("https://boards-api.greenhouse.io/v1/boards/spotify").mock(
        return_value=httpx.Response(200, json={"name": name})
    )


@respx.mock
def test_search_jobs_returns_raw_jobs_from_api():
    _mock_metadata()
    respx.get("https://boards-api.greenhouse.io/v1/boards/spotify/jobs").mock(
        return_value=httpx.Response(200, json={"jobs": [RAW_JOB]})
    )
    crawler = GreenhouseCrawler(board_token="spotify")

    jobs = crawler.search_jobs()

    assert jobs == [RAW_JOB]


@respx.mock
def test_search_jobs_fetches_and_caches_company_display_name():
    metadata_route = _mock_metadata(name="Spotify AB")
    respx.get("https://boards-api.greenhouse.io/v1/boards/spotify/jobs").mock(
        return_value=httpx.Response(200, json={"jobs": [RAW_JOB]})
    )
    crawler = GreenhouseCrawler(board_token="spotify")

    crawler.search_jobs()
    crawler.search_jobs()
    dto = crawler.parse_job(RAW_JOB)

    assert metadata_route.call_count == 1  # so busca uma vez, depois usa cache
    assert dto.company == "Spotify AB"


@respx.mock
def test_search_jobs_falls_back_to_board_token_when_metadata_fetch_fails():
    respx.get("https://boards-api.greenhouse.io/v1/boards/spotify").mock(
        return_value=httpx.Response(500)
    )
    respx.get("https://boards-api.greenhouse.io/v1/boards/spotify/jobs").mock(
        return_value=httpx.Response(200, json={"jobs": [RAW_JOB]})
    )
    crawler = GreenhouseCrawler(board_token="spotify")

    crawler.search_jobs()
    dto = crawler.parse_job(RAW_JOB)

    assert dto.company == "spotify"


def test_parse_job_uses_board_token_when_company_name_not_yet_fetched():
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
    _mock_metadata()
    broken_job = {"id": 999, "title": "Sem URL"}  # falta absolute_url -> KeyError no parse_job
    respx.get("https://boards-api.greenhouse.io/v1/boards/spotify/jobs").mock(
        return_value=httpx.Response(200, json={"jobs": [RAW_JOB, broken_job]})
    )
    crawler = GreenhouseCrawler(board_token="spotify")

    jobs = crawler.collect()

    assert len(jobs) == 1
    assert jobs[0].external_id == "12345"
