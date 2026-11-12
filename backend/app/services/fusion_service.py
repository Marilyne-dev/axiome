"""Commissariat à la fusion : contrôle de la parité d'échange et des apports.

Le commissaire à la fusion apprécie le caractère équitable du rapport d'échange et vérifie
que l'actif net apporté n'est pas surévalué (au moins égal à l'augmentation de capital).
Les évaluations sont saisies par méthode ; la valeur retenue par société est, par défaut,
la moyenne des méthodes (approche de travail, à pondérer selon le jugement du commissaire).
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.fusion import FusionDossier, FusionEvaluation

METHODES = ["ANC (actif net comptable)", "ANR (actif net réévalué)",
            "Rendement / DCF", "Comparables de marché", "Autre"]

SEUIL_ECART = 0.05  # 5 % : au-delà, l'écart de parité mérite justification


def ensure(db: Session, mission_id: int) -> FusionDossier:
    dossier = db.query(FusionDossier).filter_by(mission_id=mission_id).first()
    if not dossier:
        dossier = FusionDossier(mission_id=mission_id)
        db.add(dossier)
        db.commit()
        db.refresh(dossier)
    return dossier


def set_dossier(db: Session, mission_id: int, **champs) -> None:
    dossier = ensure(db, mission_id)
    for k in ("nom_absorbante", "nom_absorbee"):
        if champs.get(k) is not None:
            setattr(dossier, k, str(champs[k])[:160])
    for k in ("actions_absorbante", "actions_absorbee", "parite_num", "parite_den"):
        if champs.get(k) is not None:
            setattr(dossier, k, max(0, int(champs[k])))
    if champs.get("valeur_nominale") is not None:
        dossier.valeur_nominale = max(0.0, float(champs["valeur_nominale"]))
    if dossier.parite_den == 0:
        dossier.parite_den = 1
    db.commit()


def ajouter_evaluation(db: Session, mission_id: int, societe: str,
                       methode: str, valeur: float) -> None:
    if societe not in ("A", "B"):
        return
    db.add(FusionEvaluation(mission_id=mission_id, societe=societe,
                            methode=(methode or "Autre")[:80], valeur=float(valeur)))
    db.commit()


def supprimer_evaluation(db: Session, mission_id: int, eval_id: int) -> None:
    e = db.get(FusionEvaluation, eval_id)
    if e and e.mission_id == mission_id:
        db.delete(e)
        db.commit()


def _valeur_retenue(evals: list[FusionEvaluation]) -> float:
    vals = [e.valeur for e in evals]
    return round(sum(vals) / len(vals), 2) if vals else 0.0


def etat(db: Session, mission_id: int) -> dict:
    dossier = ensure(db, mission_id)
    evals = db.query(FusionEvaluation).filter_by(mission_id=mission_id).order_by(
        FusionEvaluation.id).all()
    eval_a = [e for e in evals if e.societe == "A"]
    eval_b = [e for e in evals if e.societe == "B"]
    va, vb = _valeur_retenue(eval_a), _valeur_retenue(eval_b)
    na, nb = dossier.actions_absorbante, dossier.actions_absorbee
    vu_a = round(va / na, 4) if na else 0.0     # valeur unitaire absorbante
    vu_b = round(vb / nb, 4) if nb else 0.0     # valeur unitaire absorbée
    parite_theorique = round(vu_b / vu_a, 4) if vu_a else 0.0  # actions A pour 1 action B
    parite_retenue = round(dossier.parite_num / dossier.parite_den, 4) if dossier.parite_den else 0.0
    if parite_theorique:
        ecart = round((parite_retenue - parite_theorique) / parite_theorique, 4)
    else:
        ecart = None
    # actions A à créer = parité retenue × nombre d'actions absorbée
    actions_creees = round(parite_retenue * nb)
    augmentation_capital = round(actions_creees * dossier.valeur_nominale, 2)
    actif_net_apporte = vb  # valeur retenue de l'absorbée
    prime_fusion = round(actif_net_apporte - augmentation_capital, 2)
    controle_apport = prime_fusion >= 0  # actif net apporté ≥ augmentation de capital

    alertes = []
    if ecart is not None and abs(ecart) > SEUIL_ECART:
        sens = "supérieure" if ecart > 0 else "inférieure"
        alertes.append(f"Parité retenue {sens} de {abs(ecart) * 100:.1f}% à la parité théorique.")
    if not controle_apport:
        alertes.append("Actif net apporté inférieur à l'augmentation de capital (apport insuffisant).")
    if not eval_a or not eval_b:
        alertes.append("Évaluations incomplètes (au moins une méthode par société).")

    if not eval_a or not eval_b or not na or not nb:
        conclusion = "Données incomplètes : renseigner actions et évaluations."
    elif alertes:
        conclusion = "Points à justifier avant conclusion sur le caractère équitable."
    else:
        conclusion = ("Rapport d'échange cohérent avec les valeurs retenues ; "
                      "actif net apporté au moins égal à l'augmentation de capital.")

    return {
        "dossier": dossier,
        "eval_a": eval_a, "eval_b": eval_b, "methodes": METHODES,
        "valeur_a": va, "valeur_b": vb, "vu_a": vu_a, "vu_b": vu_b,
        "parite_theorique": parite_theorique, "parite_retenue": parite_retenue,
        "parite_num": dossier.parite_num, "parite_den": dossier.parite_den,
        "ecart": ecart, "seuil_ecart": SEUIL_ECART,
        "actions_creees": actions_creees, "augmentation_capital": augmentation_capital,
        "actif_net_apporte": actif_net_apporte, "prime_fusion": prime_fusion,
        "controle_apport": controle_apport, "alertes": alertes, "conclusion": conclusion,
    }
