import logging

import anthropic

from app.ai.analyzer import Analyzer
from app.config import settings
from app.crawler.greenhouse import GreenhouseCrawler
from app.crawler.runner import CrawlerRunner
from app.database.database import SessionLocal
from app.database.models import Job, User
from app.logging_config import configure_logging
from app.notifications.telegram import TelegramNotifier
from app.services.analysis_service import analyze_job_for_user
from app.services.notification_service import notify_user_about_job

logger = logging.getLogger(__name__)


def run_once() -> None:
    """Executa um ciclo completo: coleta -> analise -> notificacao.

    Ponto de entrada manual para a Sprint 2-5 (o scheduler ainda nao tem tecnologia
    definida - ver docs/po-backlog.md). Cada estagio degrada graciosamente se a
    configuracao necessaria (board tokens, CLAUDE_API_KEY, TELEGRAM_TOKEN) nao
    estiver presente, em vez de quebrar o processo inteiro.
    """
    session = SessionLocal()
    try:
        if not settings.greenhouse_board_tokens:
            logger.warning(
                "GREENHOUSE_BOARD_TOKENS vazio - nenhuma empresa configurada para rastrear "
                "(ver docs/po-backlog.md)"
            )
            return

        crawlers = [GreenhouseCrawler(board_token=t) for t in settings.greenhouse_board_tokens]
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

        users = session.query(User).all()
        jobs = session.query(Job).all()

        for user in users:
            for job in jobs:
                already_analyzed = any(a.user_id == user.id for a in job.analyses)
                if already_analyzed:
                    continue

                analysis = analyze_job_for_user(session, analyzer, user, job)
                if analysis is None or notifier is None:
                    continue

                notify_user_about_job(session, notifier, user, job, analysis)
    finally:
        session.close()


if __name__ == "__main__":
    configure_logging()
    run_once()
