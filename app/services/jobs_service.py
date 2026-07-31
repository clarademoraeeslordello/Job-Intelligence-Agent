import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.crawler.base import JobDTO
from app.database.models import Job

logger = logging.getLogger(__name__)


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
    seen_in_batch: set[tuple[str, str]] = set()

    for dto in job_dtos:
        if not dto.url or not dto.source or not dto.external_id:
            skipped_invalid += 1
            continue

        key = (dto.source, dto.external_id)
        if key in seen_in_batch:
            # A mesma fonte pode retornar a mesma vaga 2x num unico crawl (ex:
            # sobreposicao de paginacao). A sessao usa autoflush=False, entao um
            # SELECT nao enxergaria um insert ainda nao commitado desta mesma
            # chamada - sem essa checagem em memoria, a 2a insercao so falharia
            # no commit final, quebrando o lote inteiro (nao so a vaga duplicada).
            skipped_duplicate += 1
            continue

        already_exists = session.execute(
            select(Job.id).where(Job.source == dto.source, Job.external_id == dto.external_id)
        ).first()
        if already_exists:
            skipped_duplicate += 1
            continue

        seen_in_batch.add(key)
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

    try:
        session.commit()
    except IntegrityError:
        # Defesa em profundidade: se algum caso de duplicata escapar das checagens
        # acima, um commit falho nao pode deixar a sessao "envenenada" (SQLAlchemy
        # exige rollback antes de qualquer novo uso) para o resto da execucao -
        # isso ja quebrou analise e notificacao numa execucao real de producao.
        session.rollback()
        logger.exception("commit de vagas falhou por violacao de unicidade, revertido")
        created = 0

    return SaveJobsResult(
        found=found,
        created=created,
        skipped_duplicate=skipped_duplicate,
        skipped_invalid=skipped_invalid,
    )
