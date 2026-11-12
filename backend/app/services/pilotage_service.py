"""Module dashboards de pilotage — indicateurs transversaux du cabinet."""
from __future__ import annotations

from collections import Counter

from sqlalchemy.orm import Session

from app.models.audit import RiskItem
from app.models.client import Client
from app.models.conclusion import CycleConclusion
from app.models.controle_interne import ControleInterne
from app.models.mission import Cycle, Mission
from app.services.risque_service import niveau as niveau_risque


def _niveau_max(risques: list[RiskItem]) -> str:
    ordre = {"faible": 0, "modere": 1, "eleve": 2, "critique": 3}
    niveaux = [niveau_risque(r.score) for r in risques]
    return max(niveaux, key=lambda n: ordre.get(n, 0)) if niveaux else "—"


def synthese(db: Session, cabinet_id: int | None = None) -> dict:
    """Indicateurs globaux + une ligne de pilotage par mission.

    `cabinet_id` cloisonne les données à un cabinet (obligatoire pour tout utilisateur
    de cabinet). `None` = vue plateforme, réservée à l'éditeur.
    """
    mq = db.query(Mission).filter(Mission.is_archived.is_(False))
    cq = db.query(Client).filter(Client.is_archived.is_(False))
    if cabinet_id is not None:
        mq = mq.join(Client, Mission.client_id == Client.id).filter(Client.cabinet_id == cabinet_id)
        cq = cq.filter(Client.cabinet_id == cabinet_id)
    missions = mq.all()
    clients = cq.count()

    par_referentiel: Counter[str] = Counter()
    risques_par_niveau: Counter[str] = Counter()
    lignes: list[dict] = []

    for m in missions:
        par_referentiel[m.referentiel] += 1
        risques = db.query(RiskItem).filter_by(mission_id=m.id).all()
        for r in risques:
            risques_par_niveau[niveau_risque(r.score)] += 1

        conclusions = db.query(CycleConclusion).filter_by(mission_id=m.id).all()
        nb_anomalies = sum(1 for c in conclusions if c.anomalie)
        nb_cycles = db.query(Cycle).filter_by(mission_id=m.id).count()
        ci_deficients = (
            db.query(ControleInterne)
            .join(Cycle, ControleInterne.cycle_id == Cycle.id)
            .filter(Cycle.mission_id == m.id, ControleInterne.conclusion == "deficient")
            .count()
        )
        lignes.append({
            "mission": m,
            "nb_cycles": nb_cycles,
            "nb_conclusions": len(conclusions),
            "nb_anomalies": nb_anomalies,
            "nb_risques": len(risques),
            "risque_max": _niveau_max(risques),
            "ci_deficients": ci_deficients,
            "avancement": round(100 * len(conclusions) / nb_cycles) if nb_cycles else 0,
        })

    return {
        "nb_missions": len(missions),
        "nb_clients": clients,
        "par_referentiel": dict(par_referentiel),
        "risques_par_niveau": {k: risques_par_niveau.get(k, 0)
                               for k in ("faible", "modere", "eleve", "critique")},
        "missions_avec_anomalies": sum(1 for l in lignes if l["nb_anomalies"] or l["ci_deficients"]),
        "lignes": lignes,
    }
