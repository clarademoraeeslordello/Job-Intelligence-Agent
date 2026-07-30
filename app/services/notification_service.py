import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import Job, JobAnalysis, Notification, User
from app.notifications.telegram import TelegramNotifier, format_job_notification

logger = logging.getLogger(__name__)


def notify_user_about_job(
    session: Session,
    notifier: TelegramNotifier,
    user: User,
    job: Job,
    analysis: JobAnalysis,
) -> Notification | None:
    """Notifica o usuario sobre uma vaga, respeitando as regras de produto:

    - nunca notifica duas vezes a mesma vaga para o mesmo usuario (unique constraint
      (user_id, job_id) + checagem previa, ver database-design.md secao 4);
    - so notifica se o usuario tiver telegram_chat_id cadastrado;
    - so notifica se o score atingir o limite minimo configurado no perfil do usuario
      (Profile.notification_score_threshold, ver roadmap.md Fase 5).
    """
    if not user.telegram_chat_id:
        logger.info("user_id=%s sem telegram_chat_id, notificacao ignorada", user.id)
        return None

    threshold = user.profile.notification_score_threshold if user.profile else 80.0
    if analysis.score < threshold:
        return None

    already_notified = session.execute(
        select(Notification.id).where(
            Notification.user_id == user.id, Notification.job_id == job.id
        )
    ).first()
    if already_notified:
        return None

    text = format_job_notification(job, analysis)
    status = "sent"
    try:
        notifier.send(user.telegram_chat_id, text)
    except Exception:
        logger.exception("falha ao enviar notificacao user_id=%s job_id=%s", user.id, job.id)
        status = "failed"

    notification = Notification(user_id=user.id, job_id=job.id, channel="telegram", status=status)
    session.add(notification)
    session.commit()
    return notification
