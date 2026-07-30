import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.crawler.base import BaseCrawler, JobDTO
from app.crawler.runner import CrawlerRunner
from app.database.models import Base


class WorkingCrawler(BaseCrawler):
    source_name = "working"

    def search_jobs(self) -> list[dict]:
        return [{"id": 1}]

    def parse_job(self, raw_job: dict) -> JobDTO:
        return JobDTO(
            title="Vaga",
            company="acme",
            location=None,
            country=None,
            remote=False,
            salary=None,
            description="desc",
            requirements=None,
            url="https://x.com/1",
            source=self.source_name,
            external_id=str(raw_job["id"]),
        )


class BrokenCrawler(BaseCrawler):
    source_name = "broken"

    def search_jobs(self) -> list[dict]:
        raise RuntimeError("fonte fora do ar")

    def parse_job(self, raw_job: dict) -> JobDTO:
        raise NotImplementedError


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_runner_isolates_failure_in_one_crawler(session):
    runner = CrawlerRunner([WorkingCrawler(), BrokenCrawler()])

    results = runner.run(session)

    assert results["working"].created == 1
    assert results["broken"] is None
