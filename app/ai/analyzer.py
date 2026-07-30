import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential

from app.ai.context_builder import UserContext
from app.ai.prompts import SYSTEM_PROMPT, build_user_message
from app.database.models import Job

MODEL = "claude-sonnet-5"
MAX_TOKENS = 1024


class Analyzer:
    """Orquestra a chamada a Claude API (contexto + vaga -> resposta bruta).

    O client e injetavel para permitir testes sem chamar a API real (ver
    docs/development-plan.md - Fase 4 depende de CLAUDE_API_KEY real para uso em producao).
    """

    def __init__(self, client: anthropic.Anthropic) -> None:
        self._client = client

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    def analyze(self, context: UserContext, job: Job) -> str:
        message = self._client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": build_user_message(context, job)}],
        )
        return message.content[0].text
