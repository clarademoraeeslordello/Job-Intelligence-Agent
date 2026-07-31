import logging

import anthropic
from sqlalchemy.orm import Session

from app.ai.analyzer import Analyzer
from app.config import settings
from app.crawler.arbeitnow import ArbeitnowCrawler
from app.crawler.greenhouse import GreenhouseCrawler
from app.crawler.remoteok import RemoteOKCrawler
from app.crawler.runner import CrawlerRunner
from app.database.database import SessionLocal
from app.database.models import Job, User
from app.logging_config import configure_logging
from app.notifications.telegram import TelegramNotifier
from app.services.analysis_service import analyze_job_for_user
from app.services.notification_service import notify_user_about_job

logger = logging.getLogger(__name__)

MAX_JOBS_PER_RUN = 30
# Teto de vagas (mais recentes) analisadas por disparo, independente de quantos
# usuarios existem. Sem isso, a primeira execucao com credenciais processa todo o
# backlog acumulado de vagas nunca analisadas - caro e lento (ver docs/po-backlog.md).


def process_users_and_jobs(
    session: Session, analyzer: Analyzer, notifier: TelegramNotifier | None
) -> None:
    """Para cada (usuario, vaga) ainda nao analisado, gera a analise e, se houver
    notifier configurado, notifica. Extraido de run_once() para ser testavel com
    dependencias injetadas (fakes), sem precisar de credenciais reais nos testes.

    Limita a analise as MAX_JOBS_PER_RUN vagas mais recentes por disparo - vagas
    mais antigas que isso ficam sem analise (aceitavel: o objetivo e vagas
    publicadas recentemente, nao esgotar um backlog historico).
    """
    users = session.query(User).all()
    jobs = session.query(Job).order_by(Job.created_at.desc()).limit(MAX_JOBS_PER_RUN).all()

    for user in users:
        for job in jobs:
            already_analyzed = any(a.user_id == user.id for a in job.analyses)
            if already_analyzed:
                continue

            analysis = analyze_job_for_user(session, analyzer, user, job)
            if analysis is None or notifier is None:
                continue

            notify_user_about_job(session, notifier, user, job, analysis)


def run_once() -> None:
    """Executa um ciclo completo: coleta -> analise -> notificacao.

    Chamado diariamente via GitHub Actions (.github/workflows/daily-run.yml).
    Cada estagio degrada graciosamente se a configuracao necessaria (CLAUDE_API_KEY,
    TELEGRAM_TOKEN) nao estiver presente, em vez de quebrar o processo inteiro.
    """
    session = SessionLocal()
    try:
        # Arbeitnow + RemoteOK rodam sempre: busca abrangente, sem depender de lista de
        # empresas (ver docs/po-backlog.md). GreenhouseCrawler entra por empresa, se configurado.
        crawlers: list = [ArbeitnowCrawler(lookback_hours=48), RemoteOKCrawler(lookback_hours=48)]
        crawlers += [GreenhouseCrawler(board_token=t) for t in settings.greenhouse_board_tokens]
        CrawlerRunner(crawlers).run(session)

        if not settings.claude_api_key:
            logger.warning("CLAUDE_API_KEY nao configurada - pulando etapa de analise/notificacao")
            return

        analyzer = Analyzer(client=anthropic.Anthropic(api_key=settings.claude_api_key))
        notifier = (
            TelegramNotifier(token=settings.telegram_token) if settings.telegram_token else None
        )
        if notifier is None:
            logger.warning("TELEGRAM_TOKEN nao configurado - analises serao geradas sem notificar")

        process_users_and_jobs(session, analyzer, notifier)
    finally:
        session.close()


if __name__ == "__main__":
    configure_logging()
    run_once()
