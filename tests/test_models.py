import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.models import Base, Profile, Resume, User


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_create_user(session):
    user = User(name="Clara", email="clara@example.com")
    session.add(user)
    session.commit()

    assert user.id is not None
    assert user.created_at is not None


def test_user_email_must_be_unique(session):
    session.add(User(name="Clara", email="clara@example.com"))
    session.commit()

    session.add(User(name="Outra Clara", email="clara@example.com"))
    with pytest.raises(IntegrityError):
        session.commit()


def test_profile_and_resume_linked_to_user(session):
    user = User(name="Clara", email="clara@example.com")
    session.add(user)
    session.commit()

    profile = Profile(
        user_id=user.id,
        headline="Product Manager Senior",
        desired_roles=["Product Manager", "PO"],
        desired_locations=["Suecia", "Remoto"],
        languages=["Portugues", "Ingles"],
        remote_preference="remote",
    )
    resume = Resume(
        user_id=user.id,
        structured_json={"skills": ["python", "product management"]},
    )
    session.add_all([profile, resume])
    session.commit()

    session.refresh(user)
    assert user.profile.headline == "Product Manager Senior"
    assert user.resume.structured_json["skills"] == ["python", "product management"]
