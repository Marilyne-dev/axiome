"""Service du cadrage DSN : initialisation depuis la balance (#64x) + cadrage."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.balance import LigneBalance
from app.models.cadrage_dsn import LigneCadrageDSN


def initialiser(db: Session, mission_id: int) -> int:
    """Crée les lignes de cadrage depuis les comptes de personnel (#64x) de la balance."""
    if db.query(LigneCadrageDSN).filter_by(mission_id=mission_id).first():
        return 0  # idempotent
    lignes = [
        l for l in db.query(LigneBalance).filter_by(mission_id=mission_id).all()
        if l.compte.startswith("64")
    ]
    for l in sorted(lignes, key=lambda x: x.compte):
        db.add(LigneCadrageDSN(mission_id=mission_id, compte=l.compte,
                               libelle=l.libelle, montant_fec=l.solde_n))
    db.commit()
    return len(lignes)


def cadrage(rows: list[LigneCadrageDSN]) -> dict:
    """Totaux FEC vs DSN + écart global."""
    total_fec = round(sum(r.montant_fec for r in rows), 2)
    total_dsn = round(sum(r.montant_dsn for r in rows), 2)
    return {
        "total_fec": total_fec,
        "total_dsn": total_dsn,
        "ecart_global": round(total_fec - total_dsn, 2),
        "lignes_en_ecart": sum(1 for r in rows if abs(r.ecart) >= 0.01),
    }
