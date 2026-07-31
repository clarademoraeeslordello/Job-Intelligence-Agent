import logging

from sqlalchemy.orm import Session

from app.ai.analyzer import Analyzer
from app.ai.context_builder import build_user_context
from app.ai.scorer import InvalidAIResponseError, parse_ai_response
from app.database.models import Job, JobAnalysis, User

logger = logging.getLogger(__name__)


def analyze_job_for_user(
    session: Session, analyzer: Analyzer, user: User, job: Job
) -> JobAnalysis | None:
    """Gera uma nova JobAnalysis para o par (user, job).

    Nunca sobrescreve uma analise existente — cada chamada cria um novo registro,
    preservando historico (ver database-design.md, secao 4). Se a resposta da IA
    for invalida, registra uma JobAnalysis-marcador (score=0, IGNORE) em vez de
    nao persistir nada — sem isso, a mesma vaga era reprocessada (e re-cobrada)
    a cada disparo, pra sempre, sem nunca resolver (achado em producao). Retorna
    None nesse caso, entao nunca gera notificacao (ver ai-engine.md, secao 7).
    """
    context = build_user_context(user)

    try:
        raw_text = analyzer.analyze(context, job)
        job_score = parse_ai_response(raw_text)
    except InvalidAIResponseError:
        logger.exception("analise invalida para job_id=%s user_id=%s", job.id, user.id)
        session.add(
            JobAnalysis(
                job_id=job.id,
                user_id=user.id,
                score=0,
                recommendation="IGNORE",
                positive_points=["Analise automatica falhou - nao reprocessada"],
                negative_points=[],
                raw_ai_response={"error": "invalid_ai_response", "raw_text": raw_text},
            )
        )
        session.commit()
        return None

    analysis = JobAnalysis(
        job_id=job.id,
        user_id=user.id,
        score=job_score.score,
        recommendation=job_score.recommendation,
        positive_points=job_score.positive_points,
        negative_points=job_score.negative_points,
        raw_ai_response=job_score.raw_response,
    )
    session.add(analysis)
    session.commit()
    logger.info(
        "analise concluida job_id=%s user_id=%s score=%.0f recommendation=%s",
        job.id,
        user.id,
        job_score.score,
        job_score.recommendation,
    )
    return analysis
