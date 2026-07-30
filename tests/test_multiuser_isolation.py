import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.database.models import Base, Job, JobAnalysis, Notification, Profile, User
from app.services.notification_service import notify_user_about_job

"""Fase 6 (docs/development-plan.md): garante que a mesma vaga pode ter analises e
notificacoes diferentes por usuario, sem vazamento de dados entre contas
(ver database-design.md, nota da secao 2 e product-requirements.md)."""


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


def _make_user(session, name, email, chat_id) -> User:
    user = User(name=name, email=email, telegram_chat_id=chat_id)
    session.add(user)
    session.flush()
    session.add(Profile(user_id=user.id, notification_score_threshold=80.0))
    session.commit()
    return user


def _make_job(session) -> Job:
    job = Job(
        title="Product Manager",
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
    return job


def test_same_job_can_have_different_analysis_score_per_user(session):
    clara = _make_user(session, "Clara", "clara@example.com", "1")
    mae_da_clara = _make_user(session, "Mae da Clara", "mae@example.com", "2")
    job = _make_job(session)

    session.add(
        JobAnalysis(
            job_id=job.id,
            user_id=clara.id,
            score=95,
            recommendation="APPLY",
            positive_points=["fit forte"],
            negative_points=[],
            raw_ai_response={},
        )
    )
    session.add(
        JobAnalysis(
            job_id=job.id,
            user_id=mae_da_clara.id,
            score=20,
            recommendation="IGNORE",
            positive_points=["nenhum requisito atendido"],
            negative_points=["senioridade incompativel"],
            raw_ai_response={},
        )
    )
    session.commit()

    clara_analysis = session.execute(
        select(JobAnalysis).where(JobAnalysis.user_id == clara.id, JobAnalysis.job_id == job.id)
    ).scalar_one()
    mae_analysis = session.execute(
        select(JobAnalysis).where(
            JobAnalysis.user_id == mae_da_clara.id, JobAnalysis.job_id == job.id
        )
    ).scalar_one()

    assert clara_analysis.score == 95
    assert mae_analysis.score == 20
    assert clara_analysis.id != mae_analysis.id


def test_notification_for_one_user_never_leaks_to_another(session):
    clara = _make_user(session, "Clara", "clara@example.com", "1")
    mae_da_clara = _make_user(session, "Mae da Clara", "mae@example.com", "2")
    job = _make_job(session)
    notifier = _FakeNotifier()

    high_score_analysis = JobAnalysis(
        job_id=job.id,
        user_id=clara.id,
        score=95,
        recommendation="APPLY",
        positive_points=["fit forte"],
        negative_points=[],
        raw_ai_response={},
    )

    notify_user_about_job(session, notifier, clara, job, high_score_analysis)

    clara_notifications = (
        session.execute(select(Notification).where(Notification.user_id == clara.id))
        .scalars()
        .all()
    )
    mae_notifications = (
        session.execute(select(Notification).where(Notification.user_id == mae_da_clara.id))
        .scalars()
        .all()
    )

    assert len(clara_notifications) == 1
    assert len(mae_notifications) == 0
    assert notifier.sent == [("1", notifier.sent[0][1])]
