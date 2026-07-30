import logging

from sqlalchemy.orm import Session

from app.crawler.base import BaseCrawler
from app.services.jobs_service import SaveJobsResult, save_jobs

logger = logging.getLogger(__name__)


class CrawlerRunner:
    """Orquestra a execucao de multiplos crawlers.

    Falha em uma fonte nunca derruba as demais (ver docs/crawler-strategy.md, secao 7).
    """

    def __init__(self, crawlers: list[BaseCrawler]) -> None:
        self.crawlers = crawlers

    def run(self, session: Session) -> dict[str, SaveJobsResult | None]:
        results: dict[str, SaveJobsResult | None] = {}
        for crawler in self.crawlers:
            try:
                jobs = crawler.collect()
                result = save_jobs(session, jobs)
                results[crawler.source_name] = result
                logger.info(
                    "crawler=%s found=%d created=%d skipped_duplicate=%d skipped_invalid=%d",
                    crawler.source_name,
                    result.found,
                    result.created,
                    result.skipped_duplicate,
                    result.skipped_invalid,
                )
            except Exception:
                logger.exception("crawler=%s failed", crawler.source_name)
                results[crawler.source_name] = None
        return results
