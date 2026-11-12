"""Service du cadrage TVA collectée.

Les taux applicables dépendent du référentiel et du pays de la mission
(cloisonnement multi-référentiel) : métropole PCG, DOM Martinique, zone OHADA.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.analyse_tva import LigneTVA
from app.models.balance import LigneBalance
from app.models.mission import Mission

# Grilles de taux de TVA collectée par contexte.
_TAUX_METROPOLE = [
    ("Taux normal", 0.20), ("Taux intermédiaire", 0.10),
    ("Taux réduit", 0.055), ("Taux particulier", 0.021),
]
_TAUX_MARTINIQUE = [("Taux normal (DOM)", 0.085), ("Taux réduit (DOM)", 0.021)]
_TAUX_OHADA = [("Taux normal", 0.18)]


def taux_applicables(referentiel: str, pays: str | None) -> list[tuple[str, float]]:
    """Renvoie la grille de taux (rubrique, taux) selon le référentiel/pays."""
    if referentiel and "OHADA" in referentiel:
        return list(_TAUX_OHADA)
    if pays and "martinique" in pays.lower():
        return list(_TAUX_MARTINIQUE)
    return list(_TAUX_METROPOLE)


def initialiser(db: Session, mission_id: int) -> int:
    """Crée les lignes de TVA (une par taux applicable) ; préremplit la TVA #4457."""
    if db.query(LigneTVA).filter_by(mission_id=mission_id).first():
        return 0  # idempotent
    mission = db.get(Mission, mission_id)
    if not mission:
        raise ValueError("Mission introuvable")
    tva_collectee = round(sum(
        abs(l.solde_n) for l in db.query(LigneBalance).filter_by(mission_id=mission_id).all()
        if l.compte.startswith("4457")
    ), 2)
    grille = taux_applicables(mission.referentiel, mission.pays)
    for i, (rubrique, taux) in enumerate(grille):
        db.add(LigneTVA(mission_id=mission_id, rubrique=rubrique, taux=taux,
                        tva_comptabilisee=tva_collectee if i == 0 else 0.0))
    db.commit()
    return len(grille)


def cadrage(rows: list[LigneTVA]) -> dict:
    """Totaux TVA théorique vs comptabilisée + écart global."""
    total_theorique = round(sum(r.tva_theorique for r in rows), 2)
    total_comptabilisee = round(sum(r.tva_comptabilisee for r in rows), 2)
    return {
        "total_theorique": total_theorique,
        "total_comptabilisee": total_comptabilisee,
        "ecart_global": round(total_theorique - total_comptabilisee, 2),
        "lignes_en_ecart": sum(1 for r in rows if abs(r.ecart) >= 0.01),
    }
