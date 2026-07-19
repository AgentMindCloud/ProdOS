"""LAN-mode device pairing (spec sections 18-19).

The pairing-confirmation endpoints (``/lan/pair/*``) are intentionally
*not* behind ``require_login`` -- they're how a brand-new Android phone
proves it should be trusted, using a short-lived rate-limited code shown
on the already-authenticated desktop. Everything that manages pairing
(generating a code, revoking a device) lives under ``/settings/lan`` and
requires the desktop admin to be logged in.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from produceros.config import get_settings
from produceros.models.user import User
from produceros.services import pairing as pairing_service
from produceros.services.network import detect_private_ipv4, qr_code_data_uri
from produceros.web.app import templates
from produceros.web.context import base_context
from produceros.web.csrf import get_csrf_token, verify_csrf
from produceros.web.deps import get_session, require_login

router = APIRouter(tags=["lan"])


@router.get("/settings/lan")
async def lan_settings(request: Request, response: Response, session: Session = Depends(get_session), user: User = Depends(require_login)):
    settings = get_settings()
    devices = pairing_service.list_devices(session)
    lan_ip = detect_private_ipv4()
    csrf_token = get_csrf_token(request)
    return templates.TemplateResponse(
        request, "lan/settings.html",
        {
            **base_context(user, "settings"),
            "bind_mode": settings.bind_mode, "port": settings.port, "lan_ip": lan_ip,
            "devices": devices, "csrf_token": csrf_token, "new_pairing": None,
        },
    )


@router.post("/settings/lan/start")
async def start_pairing_route(request: Request, response: Response, session: Session = Depends(get_session), user: User = Depends(require_login)):
    settings = get_settings()
    form = await request.form()
    csrf_token = get_csrf_token(request)

    if not verify_csrf(request, form.get("csrf_token")):
        return RedirectResponse("/settings/lan", status_code=303)

    device_name = str(form.get("device_name") or "New device")
    device, code = pairing_service.start_pairing(
        session, device_name=device_name, user_id=user.id, ttl_minutes=settings.pairing_code_ttl_minutes
    )

    lan_ip = detect_private_ipv4()
    pair_url = f"http://{lan_ip}:{settings.port}/lan/pair/{device.id}?code={code}" if lan_ip else f"/lan/pair/{device.id}?code={code}"
    qr_data_uri = qr_code_data_uri(pair_url)

    devices = pairing_service.list_devices(session)
    return templates.TemplateResponse(
        request, "lan/settings.html",
        {
            **base_context(user, "settings"),
            "bind_mode": settings.bind_mode, "port": settings.port, "lan_ip": lan_ip,
            "devices": devices, "csrf_token": csrf_token,
            "new_pairing": {"device": device, "code": code, "url": pair_url, "qr_data_uri": qr_data_uri, "ttl_minutes": settings.pairing_code_ttl_minutes},
        },
    )


@router.post("/settings/lan/devices/{device_id}/revoke")
async def revoke_device_route(device_id: str, request: Request, session: Session = Depends(get_session), user: User = Depends(require_login)):
    from produceros.models.user import PairedDevice

    device = session.get(PairedDevice, uuid.UUID(device_id))
    form = await request.form()
    if device and verify_csrf(request, form.get("csrf_token")):
        pairing_service.revoke_device(session, device, user_id=user.id)
    return RedirectResponse("/settings/lan", status_code=303)


# ------------------------------------------------------------- Phone-side pairing (no login required)
@router.get("/lan/pair/{device_id}")
async def pair_confirm_form(device_id: str, request: Request, response: Response, code: str = "", session: Session = Depends(get_session)):
    csrf_token = get_csrf_token(request)
    return templates.TemplateResponse(
        request, "lan/pair.html", {"device_id": device_id, "code": code, "csrf_token": csrf_token, "error": None}
    )


@router.post("/lan/pair/{device_id}/confirm")
async def pair_confirm_submit(device_id: str, request: Request, response: Response, session: Session = Depends(get_session)):
    settings = get_settings()
    form = await request.form()
    csrf_token = get_csrf_token(request)
    submitted_code = str(form.get("code") or "").strip().upper()
    ip_address = request.client.host if request.client else "unknown"

    if not verify_csrf(request, form.get("csrf_token")):
        return templates.TemplateResponse(
            request, "lan/pair.html",
            {"device_id": device_id, "code": submitted_code, "csrf_token": csrf_token, "error": "Your session expired. Reload and try again."},
            status_code=400,
        )

    try:
        device, token = pairing_service.confirm_pairing(
            session, device_id=uuid.UUID(device_id), submitted_code=submitted_code,
            ip_address=ip_address, max_attempts_per_minute=settings.pairing_rate_limit_per_minute,
        )
    except pairing_service.RateLimitedError:
        return templates.TemplateResponse(
            request, "lan/pair.html",
            {"device_id": device_id, "code": submitted_code, "csrf_token": csrf_token, "error": "Too many attempts. Please wait a minute."},
            status_code=429,
        )
    except pairing_service.PairingError as exc:
        return templates.TemplateResponse(
            request, "lan/pair.html",
            {"device_id": device_id, "code": submitted_code, "csrf_token": csrf_token, "error": str(exc)},
            status_code=400,
        )

    secret_key = settings.load_or_create_secret_key()
    device_cookie = pairing_service.issue_device_cookie_token(secret_key, device)

    redirect = RedirectResponse("/", status_code=303)
    redirect.set_cookie(
        pairing_service.DEVICE_COOKIE_NAME, device_cookie, httponly=True, samesite="lax",
        secure=request.url.scheme == "https", max_age=pairing_service.SESSION_LIFETIME_DAYS * 86400,
    )
    return redirect
