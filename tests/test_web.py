import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.database import get_session
from app.database.models import Base, User
from app.web.app import app
from app.web.security import hash_password


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = session_local()

    def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session
    yield session
    app.dependency_overrides.clear()
    session.close()


@pytest.fixture
def client(db_session):
    return TestClient(app)


def _make_admin(session, email="admin@example.com", password="s3cret-pass") -> User:
    user = User(
        name="Admin",
        email=email,
        is_admin=True,
        is_active=True,
        password_hash=hash_password(password),
    )
    session.add(user)
    session.commit()
    return user


def test_login_page_renders(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert "Entrar" in response.text


def test_login_with_correct_credentials_redirects_and_sets_cookie(client, db_session):
    _make_admin(db_session)

    response = client.post(
        "/login",
        data={"email": "admin@example.com", "password": "s3cret-pass"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/"
    assert client.cookies.get("job_agent_session")


def test_login_with_wrong_password_shows_error(client, db_session):
    _make_admin(db_session)

    response = client.post("/login", data={"email": "admin@example.com", "password": "errada"})

    assert response.status_code == 200
    assert "invalidos" in response.text


def test_login_with_inactive_user_is_rejected(client, db_session):
    user = _make_admin(db_session)
    user.is_active = False
    db_session.commit()

    response = client.post("/login", data={"email": "admin@example.com", "password": "s3cret-pass"})

    assert "invalidos" in response.text


def test_admin_page_requires_login(client):
    response = client.get("/admin", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_admin_page_forbidden_for_non_admin_user(client, db_session):
    db_session.add(
        User(
            name="Regular",
            email="user@example.com",
            is_admin=False,
            is_active=True,
            password_hash=hash_password("senha123"),
        )
    )
    db_session.commit()
    client.post("/login", data={"email": "user@example.com", "password": "senha123"})

    response = client.get("/admin")

    assert response.status_code == 403


def test_admin_can_create_new_user_with_temporary_password(client, db_session):
    _make_admin(db_session)
    client.post("/login", data={"email": "admin@example.com", "password": "s3cret-pass"})

    response = client.post(
        "/admin/users", data={"name": "Mae da Clara", "email": "mae@example.com"}
    )

    assert response.status_code == 200
    assert "criado" in response.text
    created = db_session.execute(select(User).where(User.email == "mae@example.com")).scalar_one()
    assert created.is_active is True
    assert created.password_hash is not None


def test_admin_cannot_create_duplicate_email(client, db_session):
    _make_admin(db_session)
    client.post("/login", data={"email": "admin@example.com", "password": "s3cret-pass"})

    response = client.post(
        "/admin/users", data={"name": "Outro Admin", "email": "admin@example.com"}
    )

    assert "Ja existe" in response.text


def test_admin_can_revoke_and_restore_access(client, db_session):
    admin = _make_admin(db_session)
    target = User(
        name="Mae",
        email="mae@example.com",
        is_admin=False,
        is_active=True,
        password_hash=hash_password("x"),
    )
    db_session.add(target)
    db_session.commit()
    client.post("/login", data={"email": "admin@example.com", "password": "s3cret-pass"})

    client.post(f"/admin/users/{target.id}/toggle-active", follow_redirects=False)
    db_session.refresh(target)
    assert target.is_active is False

    client.post(f"/admin/users/{target.id}/toggle-active", follow_redirects=False)
    db_session.refresh(target)
    assert target.is_active is True


def test_admin_cannot_revoke_own_access(client, db_session):
    admin = _make_admin(db_session)
    client.post("/login", data={"email": "admin@example.com", "password": "s3cret-pass"})

    client.post(f"/admin/users/{admin.id}/toggle-active", follow_redirects=False)

    db_session.refresh(admin)
    assert admin.is_active is True
