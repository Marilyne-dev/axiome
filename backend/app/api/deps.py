"""Dépendances FastAPI : extraction de l'utilisateur courant et garde RBAC."""
from __future__ import annotations

from collections.abc import Callable

import jwt
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import TOKEN_TYPE_ACCESS, decode_token
from app.models.user import User


def _extract_token(request: Request) -> str | None:
    """Récupère le JWT depuis l'en-tête Authorization ou le cookie de session."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return request.cookies.get("access_token")


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Valide le jeton d'accès et retourne l'utilisateur actif correspondant."""
    token = _extract_token(request)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Non authentifié")
    try:
        payload = decode_token(token)
    except jwt.PyJWTError as exc:  # expiré / signature invalide
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Jeton invalide") from exc
    if payload.get("type") != TOKEN_TYPE_ACCESS:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Type de jeton incorrect")

    user = db.query(User).filter(User.email == payload.get("sub")).first()
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Utilisateur inconnu ou inactif")
    return user


def require_role(*roles: str) -> Callable[[User], User]:
    """Fabrique une dépendance exigeant l'un des rôles indiqués."""

    def _guard(user: User = Depends(get_current_user)) -> User:
        if user.has_role("SUPERADMIN") or user.has_role("ADMIN") or any(user.has_role(r) for r in roles):
            return user
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Rôle insuffisant")

    return _guard


def require_permission(code: str) -> Callable[[User], User]:
    """Fabrique une dépendance exigeant une permission 'domaine:action'."""

    def _guard(user: User = Depends(get_current_user)) -> User:
        if user.has_permission(code) or user.has_role("ADMIN") or user.has_role("SUPERADMIN"):
            return user
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Permission requise : " + code)

    return _guard


def require_lcbft(user: User = Depends(get_current_user)) -> User:
    """Garde stricte pour le module LCB-FT : correspondant habilité UNIQUEMENT.

    Aucune dérogation ADMIN : la confidentialité des données LCB-FT/TRACFIN prime.
    """
    if user.has_role("CORRESPONDANT_LCBFT"):
        return user
    raise HTTPException(status.HTTP_403_FORBIDDEN, "Accès réservé au correspondant LCB-FT")
