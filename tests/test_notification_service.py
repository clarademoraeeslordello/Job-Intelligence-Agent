import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.database.models import Base, Job, JobAnalysis, Notification, Profile, User
from app.services.notification_service import notify_user_about_job


class _FakeNotifier:
    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.sent: list[tuple[str, str]] = []

    def send(self, chat_id: str, text: str) -> None:
        if self.should_fail:
            raise RuntimeError("telegram fora do ar")
        self.sent.append((chat_id, text))


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def _setup(session, telegram_chat_id="42", threshold=80.0) -> tuple[User, Job]:
    user = User(name="Clara", email="clara@example.com", telegram_chat_id=telegram_chat_id)
    session.add(user)
    session.flush()
    session.add(Profile(user_id=user.id, notification_score_threshold=threshold))
    job = Job(
        title="PM",
        company="acme",
        location="Remote",
        country=None,
        remote=True,
        salary=None,
        description="desc",
        requirements=None,
        url="https://x.com/1",
        source="greenhouse",
        external_id="1",
    )
    session.add(job)
    session.commit()
    return user, job


def _analysis_for(job: Job, score: float) -> JobAnalysis:
    return JobAnalysis(
        job_id=job.id,
        user_id=None,
        score=score,
        recommendation="APPLY",
        positive_points=["bom fit"],
        negative_points=[],
        raw_ai_response={},
    )


def test_notify_sends_and_creates_notification_when_score_above_threshold(session):
    user, job = _setup(session)
    notifier = _FakeNotifier()

    result = notify_user_about_job(session, notifier, user, job, _analysis_for(job, score=90))

    assert result is not None
    assert result.status == "sent"
    assert notifier.sent == [("42", notifier.sent[0][1])]


def test_notify_skips_when_score_below_threshold(session):
    user, job = _setup(session, threshold=80.0)
    notifier = _FakeNotifier()

    result = notify_user_about_job(session, notifier, user, job, _analysis_for(job, score=50))

    assert result is None
    assert notifier.sent == []


def test_notify_skips_when_user_has_no_telegram_chat_id(session):
    user, job = _setup(session, telegram_chat_id=None)
    notifier = _FakeNotifier()

    result = notify_user_about_job(session, notifier, user, job, _analysis_for(job, score=95))

    assert result is None


def test_notify_never_sends_duplicate_notification_for_same_user_and_job(session):
    user, job = _setup(session)
    notifier = _FakeNotifier()

    notify_user_about_job(session, notifier, user, job, _analysis_for(job, score=95))
    second_result = notify_user_about_job(
        session, notifier, user, job, _analysis_for(job, score=95)
    )

    assert second_result is None
    assert len(notifier.sent) == 1
    assert session.execute(select(Notification)).scalars().all().__len__() == 1


def test_notify_records_failed_status_when_send_raises(session):
    user, job = _setup(session)
    notifier = _FakeNotifier(should_fail=True)

    result = notify_user_about_job(session, notifier, user, job, _analysis_for(job, score=95))

    assert result is not None
    assert result.status == "failed"
