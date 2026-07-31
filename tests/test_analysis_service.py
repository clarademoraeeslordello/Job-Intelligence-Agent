import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.database.models import Base, Job, JobAnalysis, User
from app.services.analysis_service import analyze_job_for_user

VALID_RESPONSE = (
    '{"score": 90, "recommendation": "APPLY", '
    '"reason": {"positive": ["bom fit"], "negative": []}}'
)


class _FakeAnalyzer:
    def __init__(self, response_text: str) -> None:
        self.response_text = response_text

    def analyze(self, context, job) -> str:
        return self.response_text


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture
def user_and_job(session):
    user = User(name="Clara", email="clara@example.com")
    job = Job(
        title="Product Manager",
        company="acme",
        location="Remote",
        country=None,
        remote=True,
        salary=None,
        description="descricao",
        requirements=None,
        url="https://x.com/1",
        source="greenhouse",
        external_id="1",
    )
    session.add_all([user, job])
    session.commit()
    return user, job


def test_analyze_job_for_user_creates_analysis(session, user_and_job):
    user, job = user_and_job
    analyzer = _FakeAnalyzer(VALID_RESPONSE)

    result = analyze_job_for_user(session, analyzer, user, job)

    assert result is not None
    assert result.score == 90
    assert result.recommendation == "APPLY"
    assert session.execute(select(JobAnalysis)).scalars().all().__len__() == 1


def test_analyze_job_for_user_returns_none_on_invalid_response(session, user_and_job):
    user, job = user_and_job
    analyzer = _FakeAnalyzer("resposta invalida, nao e json")

    result = analyze_job_for_user(session, analyzer, user, job)

    assert result is None


def test_analyze_job_for_user_records_marker_on_invalid_response_to_avoid_reprocessing(
    session, user_and_job
):
    # Achado real em producao: sem o marcador, a mesma vaga com resposta invalida
    # era reprocessada (e re-cobrada na API) a cada disparo, para sempre.
    user, job = user_and_job
    analyzer = _FakeAnalyzer("resposta invalida, nao e json")

    analyze_job_for_user(session, analyzer, user, job)

    marker = session.execute(select(JobAnalysis)).scalar_one()
    assert marker.score == 0
    assert marker.recommendation == "IGNORE"
    assert marker.raw_ai_response["error"] == "invalid_ai_response"


def test_analyze_job_for_user_does_not_reprocess_after_marker_recorded(session, user_and_job):
    user, job = user_and_job
    analyzer = _FakeAnalyzer("resposta invalida, nao e json")
    analyze_job_for_user(session, analyzer, user, job)

    already_analyzed = any(a.user_id == user.id for a in job.analyses)

    assert already_analyzed is True


def test_analyze_job_for_user_never_overwrites_previous_analysis(session, user_and_job):
    user, job = user_and_job
    analyzer = _FakeAnalyzer(VALID_RESPONSE)

    analyze_job_for_user(session, analyzer, user, job)
    analyze_job_for_user(session, analyzer, user, job)

    assert session.execute(select(JobAnalysis)).scalars().all().__len__() == 2
