"""Jetons à usage unique : génération de liens d'invitation et de réinitialisation."""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.auth_token import AuthToken
from app.models.user import User

TTL_INVITATION_H = 168  # 7 jours
TTL_RESET_H = 1


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _hash(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def creer_lien(db: Session, user: User, type_: str, chemin: str, ttl_heures: int) -> str:
    for t in (db.query(AuthToken)
              .filter_by(user_id=user.id, type=type_, used=False).all()):
        t.used = True
    raw = secrets.token_urlsafe(32)
    db.add(AuthToken(user_id=user.id, token_hash=_hash(raw), type=type_,
                     expires_at=_utcnow() + timedelta(hours=ttl_heures), used=False))
    db.commit()
    base = get_settings().base_url.rstrip("/")
    return f"{base}{chemin}?token={raw}"


def valider(db: Session, raw: str, type_: str) -> tuple[AuthToken | None, User | None]:
    if not raw:
        return None, None
    tok = (db.query(AuthToken)
           .filter_by(token_hash=_hash(raw), type=type_, used=False).first())
    if not tok or tok.expires_at < _utcnow():
        return None, None
    return tok, db.get(User, tok.user_id)


def consommer(db: Session, tok: AuthToken) -> None:
    tok.used = True
    db.commit()
