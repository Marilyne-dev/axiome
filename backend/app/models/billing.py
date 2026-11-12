"""Offres, abonnements et paiements (SaaS multi-cabinets).

Montants en unités mineures : centimes pour l'EUR, unité entière pour le XOF.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Plan(Base, TimestampMixin):
    """Offre commerciale. Quotas à 0 = illimité."""

    __tablename__ = "plans"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True, index=True, nullable=False)
    nom: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str] = mapped_column(String(255), default="")
    prix_mensuel_eur: Mapped[int] = mapped_column(Integer, default=0)   # centimes
    prix_annuel_eur: Mapped[int] = mapped_column(Integer, default=0)
    prix_mensuel_xof: Mapped[int] = mapped_column(Integer, default=0)
    prix_annuel_xof: Mapped[int] = mapped_column(Integer, default=0)
    quota_collaborateurs: Mapped[int] = mapped_column(Integer, default=0)
    quota_missions: Mapped[int] = mapped_column(Integer, default=0)
    fonctionnalites: Mapped[str] = mapped_column(Text, default="[]")    # liste JSON
    ordre: Mapped[int] = mapped_column(Integer, default=0)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Abonnement(Base, TimestampMixin):
    """Abonnement d'un cabinet à une offre (un seul actif par cabinet)."""

    __tablename__ = "abonnements"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cabinet_id: Mapped[int] = mapped_column(ForeignKey("cabinets.id", ondelete="CASCADE"), unique=True, nullable=False)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id"), nullable=False)
    # en_attente_paiement | actif | suspendu | resilie
    statut: Mapped[str] = mapped_column(String(25), default="en_attente_paiement", index=True)
    periode: Mapped[str] = mapped_column(String(10), default="mensuel")  # mensuel | annuel
    devise: Mapped[str] = mapped_column(String(3), default="EUR")        # EUR | XOF
    date_debut: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    date_fin: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Paiement(Base, TimestampMixin):
    """Tentative de paiement d'une période d'abonnement."""

    __tablename__ = "paiements"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reference: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)  # jeton public
    abonnement_id: Mapped[int] = mapped_column(ForeignKey("abonnements.id", ondelete="CASCADE"), nullable=False, index=True)
    # Offre visée par ce paiement quand il s'agit d'un changement d'offre (NULL = renouvellement de l'offre actuelle).
    plan_id: Mapped[int | None] = mapped_column(ForeignKey("plans.id"), nullable=True)
    fournisseur: Mapped[str] = mapped_column(String(20), default="")      # stripe | fedapay | test
    fournisseur_ref: Mapped[str] = mapped_column(String(120), default="", index=True)
    montant: Mapped[int] = mapped_column(Integer, nullable=False)
    devise: Mapped[str] = mapped_column(String(3), nullable=False)
    periode: Mapped[str] = mapped_column(String(10), default="mensuel")
    statut: Mapped[str] = mapped_column(String(15), default="en_attente", index=True)  # en_attente|paye|echoue
    paye_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
