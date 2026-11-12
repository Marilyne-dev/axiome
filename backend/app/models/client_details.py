"""Module 2 — Entités rattachées au client : contacts, dirigeants, comptes bancaires."""
from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Contact(Base, TimestampMixin):
    """Contact opérationnel chez le client."""

    __tablename__ = "contacts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    nom: Mapped[str] = mapped_column(String(150), nullable=False)
    fonction: Mapped[str] = mapped_column(String(120), default="")
    email: Mapped[str] = mapped_column(String(255), default="")
    telephone: Mapped[str] = mapped_column(String(40), default="")


class Dirigeant(Base, TimestampMixin):
    """Mandataire social / dirigeant du client."""

    __tablename__ = "dirigeants"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    nom: Mapped[str] = mapped_column(String(150), nullable=False)
    mandat: Mapped[str] = mapped_column(String(120), default="")     # Président, Gérant…
    date_nomination: Mapped[str] = mapped_column(String(20), default="")


class CompteBancaire(Base, TimestampMixin):
    """Compte bancaire du client (utile pour circularisations Trésorerie)."""

    __tablename__ = "comptes_bancaires"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    banque: Mapped[str] = mapped_column(String(150), nullable=False)
    iban: Mapped[str] = mapped_column(String(60), default="")
    devise: Mapped[str] = mapped_column(String(3), default="EUR")
