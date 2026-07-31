import json
import logging
import os

from app.database.database import SessionLocal
from app.database.models import Profile, Resume, User
from app.logging_config import configure_logging

logger = logging.getLogger(__name__)


def seed_user_from_env() -> None:
    """Cria ou atualiza um usuario a partir de variaveis de ambiente.

    Usado pelo workflow .github/workflows/seed-user.yml, que le esses valores de
    GitHub Secrets (nunca de workflow_dispatch inputs, que ficam visiveis no log
    publico do repositorio - ver docs/po-backlog.md).

    Variaveis esperadas:
      USER_NAME, USER_EMAIL, USER_TELEGRAM_CHAT_ID (opcional)
      PROFILE_JSON (opcional) - JSON com campos de Profile
        (headline, summary, years_experience, desired_roles, desired_locations,
         languages, salary_expectation, remote_preference, notification_score_threshold)
      RESUME_JSON (opcional) - JSON com o curriculo estruturado (skills, experience, etc.)
    """
    name = os.environ["USER_NAME"]
    email = os.environ["USER_EMAIL"]
    telegram_chat_id = os.environ.get("USER_TELEGRAM_CHAT_ID") or None
    profile_data = json.loads(os.environ.get("PROFILE_JSON", "{}"))
    resume_data = json.loads(os.environ.get("RESUME_JSON", "{}"))

    session = SessionLocal()
    try:
        user = session.query(User).filter(User.email == email).one_or_none()
        if user is None:
            user = User(name=name, email=email, telegram_chat_id=telegram_chat_id)
            session.add(user)
            session.flush()
            logger.info("usuario criado: %s", email)
        else:
            user.name = name
            user.telegram_chat_id = telegram_chat_id
            logger.info("usuario atualizado: %s", email)

        if user.profile is None:
            user.profile = Profile(user_id=user.id, **profile_data)
        else:
            for key, value in profile_data.items():
                setattr(user.profile, key, value)

        if user.resume is None:
            user.resume = Resume(user_id=user.id, structured_json=resume_data)
        else:
            user.resume.structured_json = resume_data

        session.commit()
    finally:
        session.close()


if __name__ == "__main__":
    configure_logging()
    seed_user_from_env()
