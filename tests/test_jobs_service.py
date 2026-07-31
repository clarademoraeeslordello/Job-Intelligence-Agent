import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.crawler.base import JobDTO
from app.database.models import Base, Job
from app.services.jobs_service import save_jobs


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    # autoflush=False replica app/database/database.py - foi essa combinacao que
    # deixou o bug de duplicata-no-mesmo-lote passar despercebido pelas checagens.
    with Session(engine, autoflush=False) as session:
        yield session


def _job_dto(external_id: str = "1", url: str = "https://x.com/1") -> JobDTO:
    return JobDTO(
        title="Product Manager",
        company="acme",
        location="Remote",
        country=None,
        remote=True,
        salary=None,
        description="desc",
        requirements=None,
        url=url,
        source="greenhouse",
        external_id=external_id,
    )


def test_save_jobs_creates_new_job(session):
    result = save_jobs(session, [_job_dto()])

    assert result.found == 1
    assert result.created == 1
    assert result.skipped_duplicate == 0
    assert session.execute(select(Job)).scalar_one().external_id == "1"


def test_save_jobs_deduplicates_by_source_and_external_id(session):
    save_jobs(session, [_job_dto(external_id="1")])

    result = save_jobs(session, [_job_dto(external_id="1")])

    assert result.created == 0
    assert result.skipped_duplicate == 1
    assert session.execute(select(Job)).scalars().all().__len__() == 1


def test_save_jobs_dedupes_same_job_appearing_twice_in_the_same_batch(session):
    # Reproduz o bug real de producao: a mesma fonte retornou a mesma vaga 2x
    # num unico crawl (paginacao sobreposta). Com autoflush=False, um SELECT nao
    # via o insert ainda pendente desta mesma chamada, e o 2o insert so falhava
    # no commit final - quebrando o lote inteiro, nao so a vaga duplicada.
    duplicated = _job_dto(external_id="1")

    result = save_jobs(session, [duplicated, duplicated])

    assert result.found == 2
    assert result.created == 1
    assert result.skipped_duplicate == 1
    assert session.execute(select(Job)).scalars().all().__len__() == 1


def test_save_jobs_skips_invalid_job_without_url(session):
    invalid = _job_dto(url="")

    result = save_jobs(session, [invalid])

    assert result.skipped_invalid == 1
    assert result.created == 0
