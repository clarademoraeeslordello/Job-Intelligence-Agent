import re

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.crawler.base import BaseCrawler, JobDTO

BOARDS_API_URL = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs"


def _strip_html(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html or "")
    return re.sub(r"\s+", " ", text).strip()


class GreenhouseCrawler(BaseCrawler):
    """Crawler para vagas publicadas via Greenhouse Job Board API (JSON publico, sem autenticacao).

    Usa a API oficial (boards-api.greenhouse.io) em vez de automacao de navegador: mais rapido,
    mais estavel e sem risco de bloqueio por anti-bot (ver docs/development-plan.md, secao 1.4).
    """

    source_name = "greenhouse"

    def __init__(self, board_token: str, client: httpx.Client | None = None) -> None:
        self.board_token = board_token
        self._client = client or httpx.Client(timeout=15.0)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    def search_jobs(self) -> list[dict]:
        url = BOARDS_API_URL.format(token=self.board_token)
        response = self._client.get(url, params={"content": "true"})
        response.raise_for_status()
        return response.json().get("jobs", [])

    def parse_job(self, raw_job: dict) -> JobDTO:
        location_name = (raw_job.get("location") or {}).get("name")
        remote = bool(location_name and "remote" in location_name.lower())

        return JobDTO(
            title=raw_job["title"],
            company=self.board_token,
            location=location_name,
            country=None,
            remote=remote,
            salary=None,
            description=_strip_html(raw_job.get("content", "")),
            requirements=None,
            url=raw_job["absolute_url"],
            source=self.source_name,
            external_id=str(raw_job["id"]),
        )
