import json

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app import seed
from app.database.models import Base, User


@pytest.fixture
def in_memory_session_local(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(seed, "SessionLocal", session_local)
    return session_local


def test_seed_user_from_env_creates_user_profile_and_resume(monkeypatch, in_memory_session_local):
    monkeypatch.setenv("USER_NAME", "Clara")
    monkeypatch.setenv("USER_EMAIL", "clara@example.com")
    monkeypatch.setenv("USER_TELEGRAM_CHAT_ID", "123")
    monkeypatch.setenv(
        "PROFILE_JSON",
        json.dumps({"headline": "Product Manager", "desired_roles": ["Product Manager"]}),
    )
    monkeypatch.setenv("RESUME_JSON", json.dumps({"skills": ["python"]}))

    seed.seed_user_from_env()

    with in_memory_session_local() as session:
        user = session.execute(select(User).where(User.email == "clara@example.com")).scalar_one()
        assert user.telegram_chat_id == "123"
        assert user.profile.headline == "Product Manager"
        assert user.resume.structured_json == {"skills": ["python"]}


def test_seed_user_from_env_updates_existing_user(monkeypatch, in_memory_session_local):
    monkeypatch.setenv("USER_NAME", "Clara")
    monkeypatch.setenv("USER_EMAIL", "clara@example.com")
    monkeypatch.setenv("PROFILE_JSON", json.dumps({"headline": "PM"}))
    monkeypatch.setenv("RESUME_JSON", "{}")
    seed.seed_user_from_env()

    monkeypatch.setenv("PROFILE_JSON", json.dumps({"headline": "PM Senior"}))
    seed.seed_user_from_env()

    with in_memory_session_local() as session:
        users = session.execute(select(User)).scalars().all()
        assert len(users) == 1
        assert users[0].profile.headline == "PM Senior"
