"""Sécurité applicative : hachage de mots de passe, JWT, MFA (TOTP).

- Mots de passe : bcrypt (jamais stockés en clair).
- Jetons : JWT access + refresh signés HS256.
- MFA : TOTP compatible Google Authenticator / Authy (pyotp).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt
import pyotp

from app.core.config import settings

# bcrypt impose une limite de 72 octets : on tronque proprement le secret.
_BCRYPT_MAX = 72

TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_REFRESH = "refresh"


# ---------- Mots de passe ----------
def hash_password(plain: str) -> str:
    """Retourne le hachage bcrypt d'un mot de passe en clair."""
    return bcrypt.hashpw(plain.encode("utf-8")[:_BCRYPT_MAX], bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Vérifie un mot de passe contre son hachage bcrypt (temps constant)."""
    try:
        return bcrypt.checkpw(plain.encode("utf-8")[:_BCRYPT_MAX], hashed.encode("utf-8"))
    except ValueError:
        return False


# ---------- JWT ----------
def _create_token(subject: str, token_type: str, expires: timedelta, extra: dict[str, Any] | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires,
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(subject: str, extra: dict[str, Any] | None = None) -> str:
    """Jeton d'accès court (par défaut 30 min)."""
    return _create_token(
        subject, TOKEN_TYPE_ACCESS,
        timedelta(minutes=settings.access_token_expire_minutes), extra,
    )


def create_refresh_token(subject: str) -> str:
    """Jeton de rafraîchissement long (par défaut 7 jours)."""
    return _create_token(
        subject, TOKEN_TYPE_REFRESH,
        timedelta(days=settings.refresh_token_expire_days),
    )


def decode_token(token: str) -> dict[str, Any]:
    """Décode et valide un JWT. Lève jwt.PyJWTError si invalide/expiré."""
    return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])


# ---------- MFA (TOTP) ----------
def generate_mfa_secret() -> str:
    """Génère un secret TOTP base32 à stocker pour l'utilisateur."""
    return pyotp.random_base32()


def mfa_provisioning_uri(secret: str, email: str, issuer: str = "AXIOME") -> str:
    """URI otpauth:// à encoder en QR code pour l'app d'authentification."""
    return pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name=issuer)


def verify_mfa_code(secret: str, code: str) -> bool:
    """Vérifie un code TOTP à 6 chiffres (fenêtre de tolérance ±1)."""
    return pyotp.TOTP(secret).verify(code, valid_window=1)
