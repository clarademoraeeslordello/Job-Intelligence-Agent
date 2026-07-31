from pathlib import Path

from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.database import get_session
from app.database.models import User
from app.web.deps import get_current_user, require_admin, require_login
from app.web.security import (
    SESSION_COOKIE_NAME,
    SESSION_MAX_AGE_SECONDS,
    create_session_token,
    generate_temporary_password,
    hash_password,
    verify_password,
)

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app = FastAPI(title="Job Intelligence Agent")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


@app.get("/", response_class=HTMLResponse)
def index(user: User | None = Depends(get_current_user)):
    if user is None:
        return RedirectResponse(url="/login", status_code=303)
    if user.is_admin:
        return RedirectResponse(url="/admin", status_code=303)
    return RedirectResponse(url="/me", status_code=303)


@app.get("/login", response_class=HTMLResponse)
def login_form(request: Request, user: User | None = Depends(get_current_user)):
    if user is not None:
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse(request, "login.html", {"error": None})


@app.post("/login")
def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    session: Session = Depends(get_session),
):
    user = session.execute(select(User).where(User.email == email)).scalar_one_or_none()

    invalid = (
        user is None
        or not user.is_active
        or user.password_hash is None
        or not verify_password(password, user.password_hash)
    )
    if invalid:
        return templates.TemplateResponse(
            request, "login.html", {"error": "Email ou senha invalidos, ou acesso desativado."}
        )

    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(
        SESSION_COOKIE_NAME,
        create_session_token(user.id),
        max_age=SESSION_MAX_AGE_SECONDS,
        httponly=True,
        samesite="lax",
    )
    return response


@app.get("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE_NAME)
    return response


@app.get("/me", response_class=HTMLResponse)
def me(request: Request, user: User = Depends(require_login)):
    return templates.TemplateResponse(request, "me.html", {"user": user})


@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard(
    request: Request,
    admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    users = session.execute(select(User).order_by(User.created_at)).scalars().all()
    return templates.TemplateResponse(
        request,
        "admin.html",
        {"users": users, "admin": admin, "temp_password": None, "new_user_email": None},
    )


@app.post("/admin/users", response_class=HTMLResponse)
def admin_create_user(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    is_admin: bool = Form(False),
    admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    existing = session.execute(select(User).where(User.email == email)).scalar_one_or_none()
    temp_password = None
    if existing is None:
        temp_password = generate_temporary_password()
        new_user = User(
            name=name,
            email=email,
            is_admin=is_admin,
            is_active=True,
            password_hash=hash_password(temp_password),
        )
        session.add(new_user)
        session.commit()

    users = session.execute(select(User).order_by(User.created_at)).scalars().all()
    return templates.TemplateResponse(
        request,
        "admin.html",
        {
            "users": users,
            "admin": admin,
            "temp_password": temp_password,
            "new_user_email": email,
            "error": "Ja existe um usuario com esse email." if existing else None,
        },
    )


@app.post("/admin/users/{user_id}/toggle-active")
def admin_toggle_active(
    user_id: int,
    admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    target = session.get(User, user_id)
    if target is not None and target.id != admin.id:
        target.is_active = not target.is_active
        session.commit()
    return RedirectResponse(url="/admin", status_code=303)
