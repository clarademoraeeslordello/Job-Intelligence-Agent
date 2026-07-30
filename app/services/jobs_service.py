from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crawler.base import JobDTO
from app.database.models import Job


@dataclass
class SaveJobsResult:
    found: int
    created: int
    skipped_duplicate: int
    skipped_invalid: int


def save_jobs(session: Session, job_dtos: list[JobDTO]) -> SaveJobsResult:
    """Valida, deduplica por (source, external_id) e persiste vagas coletadas.

    Nunca sobrescreve uma vaga existente; nunca insere vaga sem url/source/external_id
    (ver docs/product-requirements.md, regras de produto).
    """
    found = len(job_dtos)
    created = 0
    skipped_duplicate = 0
    skipped_invalid = 0

    for dto in job_dtos:
        if not dto.url or not dto.source or not dto.external_id:
            skipped_invalid += 1
            continue

        already_exists = session.execute(
            select(Job.id).where(Job.source == dto.source, Job.external_id == dto.external_id)
        ).first()
        if already_exists:
            skipped_duplicate += 1
            continue

        session.add(
            Job(
                title=dto.title,
                company=dto.company,
                location=dto.location,
                country=dto.country,
                remote=dto.remote,
                salary=dto.salary,
                description=dto.description,
                requirements=dto.requirements,
                url=dto.url,
                source=dto.source,
                external_id=dto.external_id,
            )
        )
        created += 1

    session.commit()
    return SaveJobsResult(
        found=found,
        created=created,
        skipped_duplicate=skipped_duplicate,
        skipped_invalid=skipped_invalid,
    )
