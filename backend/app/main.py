"""Point d'entrée FastAPI d'AXIOME.

Monte l'API (auth) et les pages web (login, tableau de bord) via Jinja2.
Démarrage local :  uvicorn app.main:app --reload
"""
from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI, Form, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app import web
from app.api import (
    routes_acceptation,
    routes_admin,
    routes_analyse,
    routes_auth,
    routes_clients,
    routes_confirmations,
    routes_controle_interne,
    routes_echantillon,
    routes_espace,
    routes_excel,
    routes_feuilles,
    routes_fraude,
    routes_ia,
    routes_import,
    routes_lcbft,
    routes_planification,
    routes_programme,
    routes_public,
    routes_rapports,
    routes_risques,
    routes_seuils,
)
from app.api.deps import get_current_user
from app.api.scope import garde_cycle, garde_mission
from app.core.config import settings
from app.core.database import engine, get_db
from app.core.i18n import t
from app.core.security import create_access_token, verify_mfa_code, verify_password
from app.models.cabinet import Cabinet
from app.models.user import User

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
templates.env.globals["t"] = t
templates.env.globals["brand_primary"] = settings.brand_primary
templates.env.globals["brand_secondary"] = settings.brand_secondary

app = FastAPI(title=settings.app_name, version="1.0.0-phase1")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.include_router(routes_auth.router)
app.include_router(routes_admin.router)
app.include_router(routes_clients.router)
app.include_router(routes_acceptation.router, dependencies=[Depends(garde_mission)])
app.include_router(routes_planification.router, dependencies=[Depends(garde_mission)])
app.include_router(routes_risques.router, dependencies=[Depends(garde_mission)])
app.include_router(routes_controle_interne.router, dependencies=[Depends(garde_cycle)])
app.include_router(routes_programme.router, dependencies=[Depends(garde_cycle)])
app.include_router(routes_feuilles.router, dependencies=[Depends(garde_cycle)])
app.include_router(routes_echantillon.router, dependencies=[Depends(garde_cycle)])
app.include_router(routes_confirmations.router, dependencies=[Depends(garde_mission)])
app.include_router(routes_import.router, dependencies=[Depends(garde_mission)])
app.include_router(routes_excel.router, dependencies=[Depends(garde_mission)])
app.include_router(routes_seuils.router, dependencies=[Depends(garde_mission)])
app.include_router(routes_analyse.router, dependencies=[Depends(garde_mission)])
app.include_router(routes_fraude.router, dependencies=[Depends(garde_mission)])
app.include_router(routes_lcbft.router)
app.include_router(routes_ia.router)
app.include_router(routes_rapports.router, dependencies=[Depends(garde_mission)])
app.include_router(routes_espace.router)
app.include_router(routes_public.router)
app.include_router(web.router)


@app.middleware("http")
async def _security_headers(request: Request, call_next):
    """Ajoute des en-têtes de sécurité à chaque réponse (durcissement)."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if settings.is_production:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.get("/healthz", include_in_schema=False)
def healthz() -> dict[str, str]:
    """Sonde de vivacité pour l'orchestrateur."""
    return {"status": "ok", "app": settings.app_name}


@app.get("/readyz", include_in_schema=False)
def readyz() -> dict[str, str]:
    """Sonde de disponibilité : vérifie la connexion à la base."""
    from sqlalchemy import text
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 — on renvoie 503 quelle que soit la cause DB
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "base de données indisponible") from exc
    return {"status": "ready"}


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def index(request: Request) -> Response:
    return templates.TemplateResponse(request, "accueil.html", {"lang": settings.default_lang})


@app.get("/login", response_class=HTMLResponse, include_in_schema=False)
def login_page(request: Request, error: str | None = None) -> Response:
    return templates.TemplateResponse(
        request, "login.html", {"lang": settings.default_lang, "error": error}
    )


@app.post("/login", response_class=HTMLResponse, include_in_schema=False)
def login_submit(
    request: Request,
    response: Response,
    email: str = Form(...),
    password: str = Form(...),
    mfa_code: str = Form(default=""),
    db: Session = Depends(get_db),
) -> Response:
    """Connexion depuis le formulaire web (pose un cookie httponly)."""
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password) or not user.is_active:
        return templates.TemplateResponse(
            request, "login.html",
            {"lang": settings.default_lang, "error": t("login.error")},
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    if user.mfa_enabled and (not user.mfa_secret or not verify_mfa_code(user.mfa_secret, mfa_code)):
        return templates.TemplateResponse(
            request, "login.html",
            {"lang": settings.default_lang, "error": t("login.error"), "mfa": True},
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    # Blocage si le cabinet de rattachement est suspendu (sauf éditeur plateforme).
    if not user.has_role("SUPERADMIN") and user.cabinet_id:
        cab = db.get(Cabinet, user.cabinet_id)
        if cab and cab.is_archived:
            return templates.TemplateResponse(
                request, "login.html",
                {"lang": settings.default_lang,
                 "error": "Cabinet suspendu. Contactez l'éditeur AXIOME."},
                status_code=status.HTTP_403_FORBIDDEN,
            )
    token = create_access_token(user.email, extra={"roles": [r.code for r in user.roles]})
    if user.has_role("SUPERADMIN"):
        cible = "/console"
    elif user.has_role("CLIENT"):
        cible = "/portail"
    else:
        cible = "/dashboard"
    resp = RedirectResponse(cible, status_code=status.HTTP_302_FOUND)
    resp.set_cookie("access_token", token, httponly=True, samesite="lax", secure=settings.is_production)
    return resp


@app.get("/logout", include_in_schema=False)
def logout() -> Response:
    resp = RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    resp.delete_cookie("access_token")
    return resp


@app.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
def dashboard(request: Request, db: Session = Depends(get_db)) -> Response:
    """Tableau de bord : accessible uniquement authentifié (cookie/JWT)."""
    try:
        user = get_current_user(request, db)
    except HTTPException:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)

    if user.has_role("CLIENT"):
        return RedirectResponse("/portail", status_code=status.HTTP_302_FOUND)
    if user.has_role("SUPERADMIN"):
        return RedirectResponse("/console", status_code=status.HTTP_302_FOUND)

    missions = web._missions_visibles(db, user)
    return templates.TemplateResponse(
        request, "dashboard.html",
        {
            "lang": user.lang,
            "user": user,
            "roles": [r.code for r in user.roles],
            "missions": missions,
        },
    )
