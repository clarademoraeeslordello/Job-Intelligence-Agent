import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.database.models import Job, JobAnalysis

TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"


def format_job_notification(job: Job, analysis: JobAnalysis) -> str:
    """Formata a mensagem de notificacao (ver architecture.md, secao 14)."""
    positive_lines = "\n".join(f"✔ {point}" for point in analysis.positive_points)

    return (
        "\U0001f680 Nova oportunidade encontrada\n\n"
        f"Empresa: {job.company}\n"
        f"Cargo: {job.title}\n"
        f"Local: {job.location or 'nao informado'}\n\n"
        f"Compatibilidade: {analysis.score:.0f}%\n\n"
        f"Motivos:\n{positive_lines}\n\n"
        f"Link: {job.url}"
    )


class TelegramNotifier:
    """Envia notificacoes via Telegram Bot API.

    Implementado com chamada HTTP direta (httpx), em vez do SDK python-telegram-bot,
    para manter o codebase sincrono e consistente com o restante do projeto (ver
    docs/po-backlog.md - decisao tecnica, nao e um bloqueio).
    """

    def __init__(self, token: str, client: httpx.Client | None = None) -> None:
        self.token = token
        self._client = client or httpx.Client(timeout=10.0)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    def send(self, chat_id: str, text: str) -> None:
        url = TELEGRAM_API_URL.format(token=self.token)
        response = self._client.post(url, json={"chat_id": chat_id, "text": text})
        response.raise_for_status()
