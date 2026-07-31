import re
from datetime import datetime, timedelta, timezone

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.crawler.base import BaseCrawler, JobDTO

API_URL = "https://remoteok.com/api"


def _strip_html(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html or "")
    return re.sub(r"\s+", " ", text).strip()


class RemoteOKCrawler(BaseCrawler):
    """Crawler abrangente via RemoteOK API (JSON publico, sem autenticacao) —
    segunda fonte agregadora, focada 100% em vagas remotas (ver docs/po-backlog.md).

    O primeiro item da resposta e sempre um aviso legal sem campo "id" — filtrado.
    """

    source_name = "remoteok"

    def __init__(self, lookback_hours: int = 48, client: httpx.Client | None = None) -> None:
        self.lookback_hours = lookback_hours
        self._client = client or httpx.Client(
            timeout=15.0, headers={"User-Agent": "job-intelligence-agent/0.1"}
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    def search_jobs(self) -> list[dict]:
        cutoff_ts = int(
            (datetime.now(timezone.utc) - timedelta(hours=self.lookback_hours)).timestamp()
        )
        response = self._client.get(API_URL)
        response.raise_for_status()
        payload = response.json()

        jobs = [item for item in payload if "id" in item]
        return [j for j in jobs if int(j.get("epoch", 0)) >= cutoff_ts]

    def parse_job(self, raw_job: dict) -> JobDTO:
        return JobDTO(
            title=raw_job["position"],
            company=raw_job["company"],
            location=raw_job.get("location") or "Remote",
            country=None,
            remote=True,
            salary=None,
            description=_strip_html(raw_job.get("description", "")),
            requirements=None,
            url=raw_job.get("apply_url") or raw_job["url"],
            source=self.source_name,
            external_id=str(raw_job["id"]),
        )
