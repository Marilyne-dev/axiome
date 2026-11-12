"""Conformité LCB-FT (module 13 bis) — données à confidentialité renforcée.

Contrainte absolue : les objets de ce module ne sont visibles ni du client,
ni des rôles non habilités. Seul le CORRESPONDANT_LCBFT (et l'ADMIN selon
politique) y accède, et toute consultation est journalisée (AuditLog).
Le screening et les déclarations TRACFIN sont des AIDES à la décision :
l'humain habilité valide toujours.
"""
from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class DossierLCBFT(Base, TimestampMixin):
    """Dossier de vigilance LCB-FT par client (KYC/KYB, classification du risque)."""

    __tablename__ = "dossiers_lcbft"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    niveau_risque: Mapped[str] = mapped_column(String(20), default="standard")  # faible|standard|eleve
    ubo: Mapped[str] = mapped_column(Text, default="")          # bénéficiaires effectifs (résumé)
    ppe: Mapped[bool] = mapped_column(Integer, default=0)       # personne politiquement exposée détectée
    statut: Mapped[str] = mapped_column(String(30), default="en_cours")

    declarations: Mapped[list["DeclarationSoupcon"]] = relationship(back_populates="dossier", lazy="selectin")


class DeclarationSoupcon(Base, TimestampMixin):
    """Déclaration de soupçon TRACFIN — CONFIDENTIEL, non divulgable au client."""

    __tablename__ = "declarations_soupcon"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dossier_id: Mapped[int] = mapped_column(ForeignKey("dossiers_lcbft.id", ondelete="CASCADE"), nullable=False)
    redacteur_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reference: Mapped[str] = mapped_column(String(60), default="")
    motif: Mapped[str] = mapped_column(Text, default="")
    statut: Mapped[str] = mapped_column(String(30), default="brouillon")  # brouillon|transmise|archivee

    dossier: Mapped[DossierLCBFT] = relationship(back_populates="declarations")
