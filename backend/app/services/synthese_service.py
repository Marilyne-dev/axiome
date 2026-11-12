"""Collecte de la synthèse de fin de mission (source unique de vérité).

Rassemble, pour une mission, les données de la feuille de garde : identité,
seuils retenus, points d'attention (anomalies par cycle, risques élevés,
contrôles internes déficients, signal Loi de Benford) et récap par cycle.

Consommé à l'identique par la génération Excel (`excel_service`) et par la
feuille de garde Word/PDF (`rapports_service`) — aucune logique dupliquée.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.cycles_ref import CYCLES, cycle_pour_cs, libelle_cycle
from app.models.audit import RiskItem, Threshold
from app.models.balance import LigneBalance
from app.models.conclusion import CycleConclusion
from app.models.controle_interne import ControleInterne
from app.models.mission import Cycle, Mission
from app.services import controles_service
from app.services.benford_service import analyse_benford
from app.services.revue_service import revue_analytique
from app.services.risque_service import niveau as niveau_risque


def _fraude_fec_dernier(db: Session, mission_id: int):
    """Dernier résultat d'analyse fraude FEC de la mission (ou None)."""
    from app.models.fraude_fec import FraudeFecResultat
    return (db.query(FraudeFecResultat).filter_by(mission_id=mission_id)
            .order_by(FraudeFecResultat.created_at.desc()).first())


def collecter(db: Session, mission_id: int) -> dict:
    """Retourne toutes les données de synthèse d'une mission (ou lève si introuvable)."""
    mission = db.get(Mission, mission_id)
    if not mission:
        raise ValueError("Mission introuvable")
    client = mission.client.raison_sociale if mission.client else ""
    cloture = str(mission.date_cloture) if mission.date_cloture else mission.exercice

    groupes: dict[str, list[LigneBalance]] = {}
    for lb in db.query(LigneBalance).filter_by(mission_id=mission_id).all():
        groupes.setdefault(cycle_pour_cs(lb.cs_standard), []).append(lb)

    seuils = db.query(Threshold).filter_by(mission_id=mission_id).first()
    conclusions = {c.cycle_code: c
                   for c in db.query(CycleConclusion).filter_by(mission_id=mission_id).all()}
    risques_eleves = sum(
        1 for r in db.query(RiskItem).filter_by(mission_id=mission_id).all()
        if niveau_risque(r.score) in ("eleve", "critique")
    )
    ci_deficients = (
        db.query(ControleInterne)
        .join(Cycle, ControleInterne.cycle_id == Cycle.id)
        .filter(Cycle.mission_id == mission_id, ControleInterne.conclusion == "deficient")
        .count()
    )

    # Récap ordonné, cycles présents uniquement.
    recap = []
    for code in CYCLES:
        lignes = groupes.get(code)
        if not lignes:
            continue
        cc = conclusions.get(code)
        recap.append({
            "code": code,
            "libelle": libelle_cycle(code),
            "nb": len(lignes),
            "total_n": round(sum(lb.solde_n for lb in lignes), 2),
            "total_n1": round(sum(lb.solde_n1 for lb in lignes), 2),
            "anomalie": bool(cc and cc.anomalie),
            "conclusion": (cc.conclusion if cc else "").strip(),
        })

    soldes = [lb.solde_n for grp in groupes.values() for lb in grp if lb.solde_n]
    benford = analyse_benford(soldes) if soldes else {"exploitable": False}

    toutes_lignes = [lb for grp in groupes.values() for lb in grp]
    controles = controles_service.controler(toutes_lignes) if toutes_lignes else {
        "controles": [], "nb_anomalies": 0}

    # Revue analytique : variations N/N-1 dépassant le seuil de signification (NEP 520).
    seuil_signif = seuils.seuil_signification if seuils else 0.0
    if toutes_lignes and seuil_signif:
        revue = revue_analytique(toutes_lignes, seuil=seuil_signif)
        variations = [ligne for ligne in revue["lignes"] if ligne["significatif"]]
    else:
        variations = []

    return {
        "mission": mission, "client": client, "cloture": cloture,
        "groupes": groupes, "seuils": seuils, "conclusions": conclusions,
        "recap": recap,
        "cycles_anomalie": sum(1 for c in conclusions.values() if c.anomalie),
        "risques_eleves": risques_eleves,
        "ci_deficients": ci_deficients,
        "benford": benford,
        "controles": controles["controles"],
        "controles_anomalies": controles["nb_anomalies"],
        "seuil_signif": seuil_signif,
        "variations_significatives": variations,
        "nb_variations_significatives": len(variations),
        "fraude_fec": _fraude_fec_dernier(db, mission_id),
    }
