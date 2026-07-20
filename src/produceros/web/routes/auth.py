"""First-run setup, login, and logout (spec section 19)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from produceros.config import get_settings
from produceros.services import auth as auth_service
from produceros.services import settings as settings_service
from produceros.web.app import templates
from produceros.web.csrf import get_csrf_token, verify_csrf
from produceros.web.deps import get_session

router = APIRouter(tags=["auth"])


@router.get("/setup")
async def setup_form(request: Request, response: Response, session: Session = Depends(get_session)):
    if auth_service.has_any_user(session) and settings_service.is_first_run_complete(session):
        return RedirectResponse("/", status_code=303)
    csrf_token = get_csrf_token(request)
    return templates.TemplateResponse(
        request, "auth/setup.html", {"csrf_token": csrf_token, "errors": [], "form": {}}
    )


@router.post("/setup")
async def setup_submit(
    request: Request, response: Response, session: Session = Depends(get_session)
):
    if auth_service.has_any_user(session) and settings_service.is_first_run_complete(session):
        return RedirectResponse("/", status_code=303)

    form = await request.form()
    csrf_token = get_csrf_token(request)

    if not verify_csrf(request, form.get("csrf_token")):
        return templates.TemplateResponse(
            request,
            "auth/setup.html",
            {
                "csrf_token": csrf_token,
                "errors": ["Your session expired. Please try again."],
                "form": form,
            },
            status_code=400,
        )

    display_name = str(form.get("display_name", "")).strip()
    username = str(form.get("username", "")).strip()
    password = str(form.get("password", ""))
    password_confirm = str(form.get("password_confirm", ""))

    errors = []
    if len(username) < 3:
        errors.append("Username must be at least 3 characters.")
    if len(password) < 10:
        errors.append("Password must be at least 10 characters.")
    if password != password_confirm:
        errors.append("Passwords do not match.")

    if errors:
        return templates.TemplateResponse(
            request,
            "auth/setup.html",
            {"csrf_token": csrf_token, "errors": errors, "form": form},
            status_code=400,
        )

    user = auth_service.create_first_admin(
        session, username=username, password=password, display_name=display_name or username
    )
    settings = get_settings()
    secret_key = settings.load_or_create_secret_key()
    token = auth_service.issue_session_token(secret_key, user)

    redirect = RedirectResponse("/", status_code=303)
    redirect.set_cookie(
        auth_service.SESSION_COOKIE_NAME,
        token,
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
        max_age=settings.session_minutes * 60,
    )
    return redirect


@router.get("/login")
async def login_form(
    request: Request, response: Response, next: str = "/", session: Session = Depends(get_session)
):
    if not auth_service.has_any_user(session) or not settings_service.is_first_run_complete(
        session
    ):
        return RedirectResponse("/setup", status_code=303)
    csrf_token = get_csrf_token(request)
    return templates.TemplateResponse(
        request, "auth/login.html", {"csrf_token": csrf_token, "error": None, "next": next}
    )


@router.post("/login")
async def login_submit(
    request: Request, response: Response, session: Session = Depends(get_session)
):
    form = await request.form()
    csrf_token = get_csrf_token(request)
    next_path = str(form.get("next") or "/")
    if not next_path.startswith("/"):
        next_path = "/"

    if not verify_csrf(request, form.get("csrf_token")):
        return templates.TemplateResponse(
            request,
            "auth/login.html",
            {
                "csrf_token": csrf_token,
                "error": "Your session expired. Please try again.",
                "next": next_path,
            },
            status_code=400,
        )

    username = str(form.get("username", ""))
    password = str(form.get("password", ""))
    ip_address = request.client.host if request.client else None

    try:
        user = auth_service.authenticate(
            session, username=username, password=password, ip_address=ip_address
        )
    except auth_service.AccountLockedError:
        return templates.TemplateResponse(
            request,
            "auth/login.html",
            {
                "csrf_token": csrf_token,
                "error": "Too many failed attempts. Please wait a minute and try again.",
                "next": next_path,
            },
            status_code=429,
        )
    except ValueError:
        return templates.TemplateResponse(
            request,
            "auth/login.html",
            {"csrf_token": csrf_token, "error": "Invalid username or password.", "next": next_path},
            status_code=400,
        )

    settings = get_settings()
    secret_key = settings.load_or_create_secret_key()
    token = auth_service.issue_session_token(secret_key, user)

    redirect = RedirectResponse(next_path, status_code=303)
    redirect.set_cookie(
        auth_service.SESSION_COOKIE_NAME,
        token,
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
        max_age=settings.session_minutes * 60,
    )
    return redirect


@router.get("/logout")
async def logout(request: Request, session: Session = Depends(get_session)):
    from produceros.web.deps import get_current_user

    user = get_current_user(request, session)
    if user is not None:
        ip_address = request.client.host if request.client else None
        auth_service.logout(session, user, ip_address=ip_address)

    redirect = RedirectResponse("/login", status_code=303)
    redirect.delete_cookie(auth_service.SESSION_COOKIE_NAME)
    return redirect
