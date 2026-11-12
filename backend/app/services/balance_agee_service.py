"""Service de la balance âgée : initialisation depuis la balance + cadrage."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.cycles_ref import cycle_pour_cs
from app.models.balance import LigneBalance
from app.models.balance_agee import BalanceAgee

# Racine de comptes par cycle (PCG/SYSCOHADA : 41 clients, 40 fournisseurs).
_RACINE = {"CLIENTS": "41", "FOURNISSEURS": "40"}


def initialiser(db: Session, mission_id: int, cycle_code: str) -> int:
    """Crée les lignes de balance âgée pour un cycle (CLIENTS/FOURNISSEURS)."""
    if cycle_code not in _RACINE:
        raise ValueError("Cycle invalide (CLIENTS | FOURNISSEURS)")
    if db.query(BalanceAgee).filter_by(mission_id=mission_id, cycle=cycle_code).first():
        return 0  # idempotent
    racine = _RACINE[cycle_code]
    lignes = [
        l for l in db.query(LigneBalance).filter_by(mission_id=mission_id).all()
        if cycle_pour_cs(l.cs_standard) == cycle_code or l.compte.startswith(racine)
    ]
    for l in lignes:
        db.add(BalanceAgee(mission_id=mission_id, cycle=cycle_code, compte=l.compte,
                           libelle=l.libelle, solde_comptable=l.solde_n))
    db.commit()
    return len(lignes)


def cadrage(rows: list[BalanceAgee]) -> dict:
    """Totaux de contrôle par tranche + écart global (solde comptable vs ventilation)."""
    def somme(attr: str) -> float:
        return round(sum(getattr(r, attr) for r in rows), 2)

    solde = somme("solde_comptable")
    ventile = round(sum(r.total_ventile for r in rows), 2)
    return {
        "solde_comptable": solde,
        "non_echu": somme("non_echu"),
        "echu_30": somme("echu_30"),
        "echu_60": somme("echu_60"),
        "echu_90": somme("echu_90"),
        "echu_plus": somme("echu_plus"),
        "total_ventile": ventile,
        "ecart_global": round(solde - ventile, 2),
        "lignes_desequilibrees": sum(1 for r in rows if abs(r.ecart) >= 0.01),
    }
