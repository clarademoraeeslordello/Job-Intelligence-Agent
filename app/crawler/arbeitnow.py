from datetime import datetime, timedelta, timezone

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.crawler.base import BaseCrawler, JobDTO

JOB_BOARD_API_URL = "https://www.arbeitnow.com/api/job-board-api"


class ArbeitnowCrawler(BaseCrawler):
    """Crawler abrangente via Arbeitnow Job Board API (JSON publico, sem autenticacao,
    sem precisar de lista de empresas especificas — cobre vagas de multiplas fontes/paises).

    So retorna vagas publicadas dentro da janela de `lookback_hours` (padrao 48h, para
    tolerar atrasos entre execucoes diarias do scheduler sem perder vagas do dia anterior).
    """

    source_name = "arbeitnow"

    def __init__(self, lookback_hours: int = 48, client: httpx.Client | None = None) -> None:
        self.lookback_hours = lookback_hours
        self._client = client or httpx.Client(timeout=15.0)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    def search_jobs(self) -> list[dict]:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=self.lookback_hours)
        cutoff_ts = int(cutoff.timestamp())

        jobs: list[dict] = []
        url: str | None = JOB_BOARD_API_URL
        while url:
            response = self._client.get(url)
            response.raise_for_status()
            payload = response.json()

            page_jobs = payload.get("data", [])
            jobs.extend(page_jobs)

            oldest_on_page = min((j.get("created_at", cutoff_ts) for j in page_jobs), default=None)
            if oldest_on_page is not None and oldest_on_page < cutoff_ts:
                break

            url = (payload.get("links") or {}).get("next")

        return [j for j in jobs if j.get("created_at", 0) >= cutoff_ts]

    def parse_job(self, raw_job: dict) -> JobDTO:
        return JobDTO(
            title=raw_job["title"],
            company=raw_job["company_name"],
            location=raw_job.get("location") or None,
            country=None,
            remote=bool(raw_job.get("remote", False)),
            salary=None,
            description=raw_job.get("description", ""),
            requirements=None,
            url=raw_job["url"],
            source=self.source_name,
            external_id=raw_job["slug"],
        )
