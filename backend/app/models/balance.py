"""Module 5 — Balance générale importée (structure calquée sur Datayoyo 'Table_BG')."""
from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class LigneBalance(Base, TimestampMixin):
    """Une ligne de balance générale rattachée à une mission.

    Colonnes inspirées de la balance Datayoyo :
    CodeEtbt, CompteName, CS_STANDARD (cycle), soldes N/N-1, mouvements,
    et classement bilan (Actif/Passif) / détail / liasse.
    """

    __tablename__ = "lignes_balance"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mission_id: Mapped[int] = mapped_column(ForeignKey("missions.id", ondelete="CASCADE"), nullable=False, index=True)

    etablissement: Mapped[str] = mapped_column(String(60), default="")
    compte: Mapped[str] = mapped_column(String(30), index=True, default="")     # n° de compte
    libelle: Mapped[str] = mapped_column(String(200), default="")
    cs_standard: Mapped[str] = mapped_column(String(80), index=True, default="") # cycle (CS_STANDARD)

    solde_n: Mapped[float] = mapped_column(Float, default=0.0)
    solde_n1: Mapped[float] = mapped_column(Float, default=0.0)
    mvt_debit_n: Mapped[float] = mapped_column(Float, default=0.0)
    mvt_credit_n: Mapped[float] = mapped_column(Float, default=0.0)

    bilan_niv2: Mapped[str] = mapped_column(String(40), default="")   # Actif | Passif
    detail_niv1: Mapped[str] = mapped_column(String(80), default="")
    liasse: Mapped[str] = mapped_column(String(120), default="")
