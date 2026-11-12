"""Import d'un FEC (Fichier des Écritures Comptables) vers la balance de la mission.

S'appuie sur `fec_service.parser_fec` (parsing + agrégats) et sur la classification
PCG des comptes (`pcg_cycles`). Remplace la balance existante de la mission
(idempotent, comme l'import de balance Datayoyo).

Note d'honnêteté : le FEC fournit les écritures de l'exercice N ; le solde N-1 n'est
pas déductible d'un FEC N seul (il faudrait le FEC N-1). Les soldes N-1 sont donc
initialisés à 0 et signalés comme tels.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.pcg_cycles import cs_standard_pour_compte
from app.models.balance import LigneBalance
from app.services.fec_service import parser_fec


def importer_fec(db: Session, mission_id: int, contenu: str) -> dict:
    """Parse un FEC, remplace la balance de la mission, retourne une synthèse."""
    res = parser_fec(contenu)

    db.query(LigneBalance).filter_by(mission_id=mission_id).delete()
    for dto in res.lignes:
        db.add(LigneBalance(
            mission_id=mission_id,
            compte=dto.compte,
            libelle=dto.libelle,
            cs_standard=cs_standard_pour_compte(dto.compte),
            solde_n=dto.solde,
            solde_n1=0.0,                       # non déductible d'un FEC N seul
            mvt_debit_n=dto.debit,
            mvt_credit_n=dto.credit,
        ))
    db.commit()

    return {
        "nb_comptes": len(res.lignes),
        "nb_ecritures": res.nb_ecritures,
        "equilibre": res.equilibre,
        "total_debit": round(res.total_debit, 2),
        "total_credit": round(res.total_credit, 2),
        "resultat_net": res.resultat_net,
        "chiffre_affaires": res.chiffre_affaires,
        "capitaux_propres": res.capitaux_propres,
    }
