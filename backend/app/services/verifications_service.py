"""Vérifications spécifiques du CAC : concordance du rapport de gestion et points de contrôle.

Le contrôle de concordance rapproche des montants déclarés dans le rapport de gestion des
montants issus des comptes (art. L.823-10 C. com.). Les montants « comptes » sont calculés
à partir de la balance importée (masses PCG et mouvements) ; ils sont indicatifs et validés
par le commissaire aux comptes.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.balance import LigneBalance
from app.models.verification import VerifConcordance, VerifPoint
from app.services.analyse_service import _somme, agregats

# (code, libellé, clé de figure auto ; "" si saisie manuelle)
CONCORDANCE = [
    ("CA", "Chiffre d'affaires", "ca"),
    ("RES", "Résultat net de l'exercice", "resultat"),
    ("CP", "Capitaux propres", "capitaux_propres"),
    ("BILAN", "Total du bilan", "total_bilan"),
    ("EFF", "Effectif moyen", ""),
]

POINTS = [
    ("RG_CONC", "Concordance du rapport de gestion avec les comptes annuels"),
    ("RG_SINC", "Sincérité des informations du rapport de gestion"),
    ("DELAIS", "Informations sur les délais de paiement (art. D.441-6)"),
    ("PARTICIP", "Prises de participation et de contrôle ; identité des détenteurs du capital"),
    ("CONV", "Conventions réglementées — établissement du rapport spécial"),
    ("EGAL", "Respect de l'égalité entre les actionnaires"),
]

TOL_ABS = 1.0     # tolérance absolue (unité de devise)
TOL_PCT = 0.005   # tolérance relative (0,5 %)


def _mouvement(lignes, prefixes: tuple[str, ...], sens: str) -> float:
    total = 0.0
    for ligne in lignes:
        c = ligne.compte or ""
        if c.startswith(prefixes):
            cr, db_ = ligne.mvt_credit_n or 0.0, ligne.mvt_debit_n or 0.0
            total += (cr - db_) if sens == "credit" else (db_ - cr)
    return round(total, 2)


def figures_comptes(lignes: list[LigneBalance]) -> dict:
    """Montants issus des comptes (best effort) pour la concordance."""
    ag = agregats(lignes)
    total_actif = round(ag["immobilisations"] + ag["stocks"]
                        + ag["creances_clients"] + ag["tresorerie_actif"], 2)
    ca = _mouvement(lignes, ("70",), "credit")
    produits = _mouvement(lignes, ("7",), "credit")
    charges = _mouvement(lignes, ("6",), "debit")
    resultat = round(produits - charges, 2)
    if ca == 0 and produits == 0 and charges == 0:  # pas de mouvements : repli sur soldes
        ca = round(abs(_somme(lignes, ("70",))), 2)
        resultat = round(abs(_somme(lignes, ("12",))), 2)
    return {"ca": ca, "resultat": resultat,
            "capitaux_propres": round(ag["capitaux_propres"], 2),
            "total_bilan": total_actif}


def _tolerance(comptes: float) -> float:
    return max(TOL_ABS, round(TOL_PCT * abs(comptes), 2))


def ensure(db: Session, mission_id: int) -> None:
    """Initialise/rafraîchit les lignes de concordance et les points de contrôle."""
    lignes = db.query(LigneBalance).filter_by(mission_id=mission_id).all()
    fig = figures_comptes(lignes) if lignes else {}
    exist = {c.code: c for c in db.query(VerifConcordance).filter_by(mission_id=mission_id).all()}
    for code, lib, key in CONCORDANCE:
        montant = float(fig.get(key, 0.0)) if key else 0.0
        row = exist.get(code)
        if not row:
            db.add(VerifConcordance(mission_id=mission_id, code=code, libelle=lib,
                                    montant_comptes=montant))
        elif key:  # rafraîchir le montant auto (les manuels restent inchangés)
            row.montant_comptes = montant
    pexist = {p.code for p in db.query(VerifPoint).filter_by(mission_id=mission_id).all()}
    for code, lib in POINTS:
        if code not in pexist:
            db.add(VerifPoint(mission_id=mission_id, code=code, libelle=lib))
    db.commit()


def set_ligne(db: Session, mission_id: int, code: str,
              montant_rapport: float | None, observation: str = "") -> None:
    row = (db.query(VerifConcordance)
           .filter_by(mission_id=mission_id, code=code).first())
    if row:
        row.montant_rapport = montant_rapport
        row.observation = (observation or "").strip()[:400]
        db.commit()


def toggle_point(db: Session, mission_id: int, code: str) -> None:
    p = (db.query(VerifPoint).filter_by(mission_id=mission_id, code=code).first())
    if p:
        p.fait = not p.fait
        db.commit()


def etat(db: Session, mission_id: int) -> dict:
    ensure(db, mission_id)
    lignes = []
    concordants = renseignes = ecarts = 0
    for row in (db.query(VerifConcordance).filter_by(mission_id=mission_id)
                .order_by(VerifConcordance.id).all()):
        tol = _tolerance(row.montant_comptes)
        if row.montant_rapport is None:
            statut, ecart = "non_renseigne", None
        else:
            ecart = round(row.montant_rapport - row.montant_comptes, 2)
            renseignes += 1
            if abs(ecart) <= tol:
                statut = "concordant"; concordants += 1
            else:
                statut = "ecart"; ecarts += 1
        lignes.append({"code": row.code, "libelle": row.libelle,
                       "montant_comptes": row.montant_comptes,
                       "montant_rapport": row.montant_rapport,
                       "ecart": ecart, "tolerance": tol, "statut": statut,
                       "observation": row.observation})
    points = [{"code": p.code, "libelle": p.libelle, "fait": p.fait,
               "observation": p.observation}
              for p in db.query(VerifPoint).filter_by(mission_id=mission_id)
              .order_by(VerifPoint.id).all()]
    points_faits = sum(1 for p in points if p["fait"])
    if ecarts:
        conclusion = f"{ecarts} écart(s) de concordance à justifier."
    elif renseignes and renseignes == len(lignes):
        conclusion = "Concordance vérifiée sur l'ensemble des montants renseignés."
    elif renseignes:
        conclusion = "Concordance partielle — compléter les montants du rapport de gestion."
    else:
        conclusion = "Vérifications à réaliser."
    return {"lignes": lignes, "points": points,
            "nb_lignes": len(lignes), "renseignes": renseignes,
            "concordants": concordants, "ecarts": ecarts,
            "points_faits": points_faits, "nb_points": len(points),
            "conclusion": conclusion}
