from dataclasses import dataclass

from app.ai.analyzer import Analyzer
from app.ai.context_builder import UserContext
from app.database.models import Job


@dataclass
class _FakeContentBlock:
    text: str


@dataclass
class _FakeMessage:
    content: list[_FakeContentBlock]


class _FakeMessages:
    def __init__(self, response_text: str) -> None:
        self.response_text = response_text
        self.last_call_kwargs: dict | None = None

    def create(self, **kwargs) -> _FakeMessage:
        self.last_call_kwargs = kwargs
        return _FakeMessage(content=[_FakeContentBlock(text=self.response_text)])


class _FakeClient:
    def __init__(self, response_text: str) -> None:
        self.messages = _FakeMessages(response_text)


def _context() -> UserContext:
    return UserContext(
        headline="PM",
        summary=None,
        years_experience=5,
        desired_roles=["Product Manager"],
        desired_locations=["Remoto"],
        languages=["Ingles"],
        salary_expectation=None,
        remote_preference="remote",
    )


def _job() -> Job:
    return Job(
        title="Product Manager",
        company="acme",
        location="Remote",
        country=None,
        remote=True,
        salary=None,
        description="descricao da vaga",
        requirements=None,
        url="https://x.com/1",
        source="greenhouse",
        external_id="1",
    )


def test_analyze_returns_raw_text_from_client():
    fake_client = _FakeClient(response_text='{"score": 90}')
    analyzer = Analyzer(client=fake_client)

    result = analyzer.analyze(_context(), _job())

    assert result == '{"score": 90}'
    assert fake_client.messages.last_call_kwargs["system"]
    assert "Product Manager" in fake_client.messages.last_call_kwargs["messages"][0]["content"]
