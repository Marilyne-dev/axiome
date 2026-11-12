"""Service du rapprochement bancaire : initialisation depuis la balance + cadrage."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.cycles_ref import cycle_pour_cs
from app.models.balance import LigneBalance
from app.models.rapprochement import RapprochementBancaire


def initialiser(db: Session, mission_id: int) -> int:
    """Crée les lignes de rapprochement depuis les comptes de trésorerie de la balance."""
    if db.query(RapprochementBancaire).filter_by(mission_id=mission_id).first():
        return 0  # déjà initialisé (idempotent)
    lignes = db.query(LigneBalance).filter_by(mission_id=mission_id).all()
    tresorerie = [l for l in lignes if cycle_pour_cs(l.cs_standard) == "TRESORERIE"]
    # un rapprochement porte sur les comptes bancaires/caisse (51x/53x)
    banques = [l for l in tresorerie if l.compte.startswith(("51", "53"))] or tresorerie
    for l in banques:
        db.add(RapprochementBancaire(mission_id=mission_id, compte=l.compte, libelle=l.libelle,
                                     solde_comptable=l.solde_n))
    db.commit()
    return len(banques)


def cadrage(rows: list[RapprochementBancaire]) -> dict:
    """Totaux de contrôle : somme comptable, somme relevés, écart global, lignes non validées."""
    tot_compta = round(sum(r.solde_comptable for r in rows), 2)
    tot_releve = round(sum(r.solde_releve for r in rows), 2)
    return {
        "total_comptable": tot_compta,
        "total_releve": tot_releve,
        "ecart_global": round(tot_compta - tot_releve, 2),
        "non_valides": sum(1 for r in rows if not r.valide),
        "lignes_avec_ecart": sum(1 for r in rows if abs(r.ecart) >= 0.01),
    }
