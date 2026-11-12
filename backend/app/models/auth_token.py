"""Jetons d'invitation / réinitialisation et boîte d'envoi e-mail (hors-ligne)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class AuthToken(Base, TimestampMixin):
    """Jeton à usage unique : activation d'un compte invité ou réinitialisation."""

    __tablename__ = "auth_tokens"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)  # invitation | reset
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class OutboxEmail(Base, TimestampMixin):
    """E-mail « envoyé » stocké lorsque SMTP n'est pas configuré (visible par l'éditeur)."""

    __tablename__ = "outbox_emails"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    destinataire: Mapped[str] = mapped_column(String(255), nullable=False)
    sujet: Mapped[str] = mapped_column(String(255), default="")
    corps: Mapped[str] = mapped_column(Text, default="")
    lien: Mapped[str] = mapped_column(String(400), default="")
