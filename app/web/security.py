import secrets

import bcrypt
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.config import settings

SESSION_COOKIE_NAME = "job_agent_session"
SESSION_MAX_AGE_SECONDS = 60 * 60 * 24 * 14  # 14 dias

# bcrypt trunca silenciosamente segredos acima de 72 bytes; cortamos explicitamente
# para evitar comportamento surpreendente com senhas muito longas.
_MAX_PASSWORD_BYTES = 72


def hash_password(password: str) -> str:
    truncated = password.encode("utf-8")[:_MAX_PASSWORD_BYTES]
    return bcrypt.hashpw(truncated, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    truncated = password.encode("utf-8")[:_MAX_PASSWORD_BYTES]
    return bcrypt.checkpw(truncated, password_hash.encode("utf-8"))


def generate_temporary_password() -> str:
    """Gera uma senha temporaria segura para exibir uma unica vez ao admin
    ao criar um novo usuario (ver app/web/routes.py)."""
    return secrets.token_urlsafe(12)


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.session_secret_key, salt="job-agent-session")


def create_session_token(user_id: int) -> str:
    return _serializer().dumps({"user_id": user_id})


def read_session_token(token: str) -> int | None:
    """Retorna o user_id do token se valido e nao expirado, senao None."""
    try:
        data = _serializer().loads(token, max_age=SESSION_MAX_AGE_SECONDS)
    except (BadSignature, SignatureExpired):
        return None
    return data.get("user_id")
