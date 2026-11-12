"""Routes d'authentification : login (mot de passe + MFA), refresh, /me."""
from __future__ import annotations

import jwt
from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.security import (
    TOKEN_TYPE_REFRESH,
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_mfa_code,
    verify_password,
)
from app.models.audit import AuditLog
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginIn(BaseModel):
    email: EmailStr
    password: str
    mfa_code: str | None = None


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    mfa_required: bool = False


@router.post("/login", response_model=TokenOut)
def login(data: LoginIn, response: Response, db: Session = Depends(get_db)) -> TokenOut:
    """Authentifie par mot de passe (bcrypt) puis MFA TOTP si activé."""
    user = db.query(User).filter(User.email == data.email).first()
    # Message générique volontaire (pas d'énumération de comptes).
    if not user or not verify_password(data.password, user.hashed_password) or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Identifiants invalides")

    if user.mfa_enabled:
        if not data.mfa_code:
            # 1re étape validée : on réclame le code MFA sans délivrer de jeton.
            return TokenOut(access_token="", refresh_token="", mfa_required=True)
        if not user.mfa_secret or not verify_mfa_code(user.mfa_secret, data.mfa_code):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Code MFA invalide")

    access = create_access_token(user.email, extra={"roles": [r.code for r in user.roles]})
    refresh = create_refresh_token(user.email)

    # Cookie httponly pour l'UI web (le front API peut aussi lire le corps JSON).
    response.set_cookie(
        "access_token", access, httponly=True, samesite="lax",
        secure=False,  # True derrière HTTPS en production
    )
    db.add(AuditLog(user_id=user.id, action="login", objet="auth", detail=user.email))
    db.commit()
    return TokenOut(access_token=access, refresh_token=refresh)


class RefreshIn(BaseModel):
    refresh_token: str


@router.post("/refresh", response_model=TokenOut)
def refresh(data: RefreshIn, db: Session = Depends(get_db)) -> TokenOut:
    """Échange un refresh token valide contre un nouveau couple de jetons."""
    try:
        payload = decode_token(data.refresh_token)
    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token invalide") from exc
    if payload.get("type") != TOKEN_TYPE_REFRESH:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Type de jeton incorrect")
    email = payload.get("sub")
    user = db.query(User).filter(User.email == email).first()
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Utilisateur invalide")
    return TokenOut(
        access_token=create_access_token(email, extra={"roles": [r.code for r in user.roles]}),
        refresh_token=create_refresh_token(email),
    )


class MeOut(BaseModel):
    email: EmailStr
    nom_complet: str
    roles: list[str]
    permissions: list[str]
    lang: str


@router.get("/me", response_model=MeOut)
def me(user: User = Depends(get_current_user)) -> MeOut:
    """Retourne le profil de l'utilisateur authentifié."""
    return MeOut(
        email=user.email,
        nom_complet=user.nom_complet,
        roles=[r.code for r in user.roles],
        permissions=sorted(user.permission_codes()),
        lang=user.lang,
    )
