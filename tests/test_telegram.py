import httpx
import respx

from app.database.models import Job, JobAnalysis
from app.notifications.telegram import TelegramNotifier, format_job_notification


def _job() -> Job:
    return Job(
        title="Product Manager",
        company="Spotify",
        location="Suecia",
        country=None,
        remote=False,
        salary=None,
        description="desc",
        requirements=None,
        url="https://boards.greenhouse.io/spotify/jobs/1",
        source="greenhouse",
        external_id="1",
    )


def _analysis() -> JobAnalysis:
    return JobAnalysis(
        job_id=1,
        user_id=1,
        score=94,
        recommendation="APPLY",
        positive_points=["Experiencia compativel", "Ingles necessario"],
        negative_points=[],
        raw_ai_response={},
    )


def test_format_job_notification_matches_expected_layout():
    text = format_job_notification(_job(), _analysis())

    assert "Empresa: Spotify" in text
    assert "Cargo: Product Manager" in text
    assert "Compatibilidade: 94%" in text
    assert "✔ Experiencia compativel" in text
    assert "https://boards.greenhouse.io/spotify/jobs/1" in text


@respx.mock
def test_send_posts_to_telegram_api():
    route = respx.post("https://api.telegram.org/bottoken123/sendMessage").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )
    notifier = TelegramNotifier(token="token123")

    notifier.send(chat_id="42", text="ola")

    assert route.called
    request = route.calls.last.request
    assert b'"chat_id":"42"' in request.content
