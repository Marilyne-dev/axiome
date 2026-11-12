"""Service de cloisonnement multi-référentiel.

Invariant : on n'applique jamais à une mission une règle fiscale d'un autre
référentiel. Toute règle est filtrée par (referentiel, pays) de la mission.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.mission import Mission
from app.models.referentiel import RegleFiscale


class ReferentielViolation(Exception):
    """Levée si une règle d'un référentiel étranger est appliquée à la mission."""


def regles_applicables(db: Session, mission: Mission) -> list[RegleFiscale]:
    """Retourne UNIQUEMENT les règles du référentiel + pays de la mission."""
    return (
        db.query(RegleFiscale)
        .filter(
            RegleFiscale.referentiel_code == mission.referentiel,
            RegleFiscale.pays == mission.pays,
        )
        .all()
    )


def appliquer_regle(mission: Mission, regle: RegleFiscale) -> float:
    """Applique une règle en refusant tout référentiel non concordant."""
    if regle.referentiel_code != mission.referentiel:
        raise ReferentielViolation(
            f"Règle '{regle.code}' du référentiel {regle.referentiel_code} "
            f"interdite sur une mission {mission.referentiel}."
        )
    return regle.taux
