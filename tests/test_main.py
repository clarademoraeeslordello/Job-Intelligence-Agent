from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.database.models import Base, Job, JobAnalysis, Notification, Profile, User
from app.main import MAX_JOBS_PER_RUN, process_users_and_jobs

VALID_RESPONSE = (
    '{"score": 90, "recommendation": "APPLY", '
    '"reason": {"positive": ["bom fit"], "negative": []}}'
)


class _FakeAnalyzer:
    def __init__(self, response_text: str = VALID_RESPONSE) -> None:
        self.response_text = response_text
        self.calls = 0

    def analyze(self, context, job) -> str:
        self.calls += 1
        return self.response_text


class _FakeNotifier:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    def send(self, chat_id: str, text: str) -> None:
        self.sent.append((chat_id, text))


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def _make_user(session, email="clara@example.com", chat_id="1") -> User:
    user = User(name="Clara", email=email, telegram_chat_id=chat_id)
    session.add(user)
    session.flush()
    session.add(Profile(user_id=user.id, notification_score_threshold=80.0))
    session.commit()
    return user


def _make_job(session, external_id="1", created_at=None) -> Job:
    job = Job(
        title="PM",
        company="acme",
        location="Remote",
        country=None,
        remote=True,
        salary=None,
        description="desc",
        requirements=None,
        url=f"https://x.com/{external_id}",
        source="greenhouse",
        external_id=external_id,
        created_at=created_at or datetime.now(timezone.utc),
    )
    session.add(job)
    session.commit()
    return job


def test_process_creates_analysis_and_notifies(session):
    user = _make_user(session)
    job = _make_job(session)
    analyzer = _FakeAnalyzer()
    notifier = _FakeNotifier()

    process_users_and_jobs(session, analyzer, notifier)

    assert session.execute(select(JobAnalysis)).scalars().all().__len__() == 1
    assert session.execute(select(Notification)).scalars().all().__len__() == 1
    assert notifier.sent


def test_process_skips_jobs_already_analyzed_for_user(session):
    user = _make_user(session)
    job = _make_job(session)
    analyzer = _FakeAnalyzer()
    notifier = _FakeNotifier()

    process_users_and_jobs(session, analyzer, notifier)
    process_users_and_jobs(session, analyzer, notifier)

    assert analyzer.calls == 1
    assert session.execute(select(JobAnalysis)).scalars().all().__len__() == 1


def test_process_generates_analysis_without_notifying_when_notifier_is_none(session):
    user = _make_user(session)
    job = _make_job(session)
    analyzer = _FakeAnalyzer()

    process_users_and_jobs(session, analyzer, notifier=None)

    assert session.execute(select(JobAnalysis)).scalars().all().__len__() == 1
    assert session.execute(select(Notification)).scalars().all() == []


def test_process_handles_multiple_users_independently(session):
    clara = _make_user(session, email="clara@example.com", chat_id="1")
    mae = _make_user(session, email="mae@example.com", chat_id="2")
    job = _make_job(session)
    analyzer = _FakeAnalyzer()
    notifier = _FakeNotifier()

    process_users_and_jobs(session, analyzer, notifier)

    analyses = session.execute(select(JobAnalysis)).scalars().all()
    assert {a.user_id for a in analyses} == {clara.id, mae.id}
    assert len(notifier.sent) == 2


def test_process_limits_to_most_recent_jobs_per_run(session):
    user = _make_user(session)
    now = datetime.now(timezone.utc)
    total_jobs = MAX_JOBS_PER_RUN + 5
    for i in range(total_jobs):
        # jobs mais antigos primeiro, para o mais recente ter i mais alto
        _make_job(session, external_id=str(i), created_at=now - timedelta(minutes=total_jobs - i))
    analyzer = _FakeAnalyzer()

    process_users_and_jobs(session, analyzer, notifier=None)

    assert analyzer.calls == MAX_JOBS_PER_RUN
    analyzed_job_ids = {a.job_id for a in session.execute(select(JobAnalysis)).scalars().all()}
    most_recent_jobs = (
        session.execute(select(Job).order_by(Job.created_at.desc()).limit(MAX_JOBS_PER_RUN))
        .scalars()
        .all()
    )
    assert analyzed_job_ids == {j.id for j in most_recent_jobs}
