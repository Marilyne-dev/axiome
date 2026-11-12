"""Service de conversion multi-devises via la table TauxDeChange."""
from __future__ import annotations

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.devise import Devise, TauxDeChange


class DeviseInconnue(Exception):
    """Devise absente du référentiel ISO 4217 chargé."""


class TauxIntrouvable(Exception):
    """Aucun taux de change disponible pour la paire demandée."""


def _assert_devise(db: Session, code: str) -> None:
    if not db.query(Devise).filter_by(code=code, actif=True).first():
        raise DeviseInconnue(code)


def convertir(db: Session, montant: float, source: str, cible: str) -> float:
    """Convertit un montant de `source` vers `cible` (taux le plus récent)."""
    if source == cible:
        return montant
    _assert_devise(db, source)
    _assert_devise(db, cible)
    taux = (
        db.query(TauxDeChange)
        .filter_by(source=source, cible=cible)
        .order_by(desc(TauxDeChange.date_taux))
        .first()
    )
    if taux:
        return round(montant * taux.taux, 6)
    # Repli : taux inverse s'il existe.
    inverse = (
        db.query(TauxDeChange)
        .filter_by(source=cible, cible=source)
        .order_by(desc(TauxDeChange.date_taux))
        .first()
    )
    if inverse and inverse.taux:
        return round(montant / inverse.taux, 6)
    raise TauxIntrouvable(f"{source}->{cible}")
