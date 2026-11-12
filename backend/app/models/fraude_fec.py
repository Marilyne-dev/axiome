"""Résultat persistant de la dernière analyse de fraude sur écritures FEC (NEP 240).

Un enregistrement par mission (le plus récent remplace le précédent), pour que le
dossier de synthèse puisse rappeler les signaux détectés sans reparser le FEC.
"""
from __future__ import annotations

from sqlalchemy import Boolean, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class FraudeFecResultat(Base, TimestampMixin):
    __tablename__ = "fraude_fec_resultats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mission_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    n_ecritures: Mapped[int] = mapped_column(Integer, default=0)
    seuil_structuration: Mapped[float] = mapped_column(Float, default=10000.0)
    structuration_nb: Mapped[int] = mapped_column(Integer, default=0)
    window_part: Mapped[float] = mapped_column(Float, default=0.0)
    window_applicable: Mapped[bool] = mapped_column(Boolean, default=False)
    window_suspicion: Mapped[bool] = mapped_column(Boolean, default=False)
    nombres_ronds_nb: Mapped[int] = mapped_column(Integer, default=0)
    doublons_nb: Mapped[int] = mapped_column(Integer, default=0)
    contrepassations_nb: Mapped[int] = mapped_column(Integer, default=0)
    tva_applicable: Mapped[bool] = mapped_column(Boolean, default=False)
    tva_taux_implicite: Mapped[float] = mapped_column(Float, default=0.0)
    tva_plausible: Mapped[bool] = mapped_column(Boolean, default=True)
    tiers_fournisseurs_nb: Mapped[int] = mapped_column(Integer, default=0)
    tiers_top_part: Mapped[float] = mapped_column(Float, default=0.0)
    tiers_ronds_nb: Mapped[int] = mapped_column(Integer, default=0)
    tiers_uniques_eleves_nb: Mapped[int] = mapped_column(Integer, default=0)
    tiers_salaires_partages_nb: Mapped[int] = mapped_column(Integer, default=0)
    fichier: Mapped[str] = mapped_column(String(255), default="")
