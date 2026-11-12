"""Détection de fraude sur écritures FEC (signaux non probants, à investiguer).

Chaque signal est un indicateur d'alerte, jamais une preuve : il oriente les
diligences de l'auditeur (NEP 240 — fraude). Aucun jugement automatique.

Détecteurs :
- structuration (smurfing) : écritures dont le montant frôle un seuil par le bas
  (fractionnement destiné à passer sous un seuil déclaratif/de contrôle) ;
- window dressing : concentration anormale de mouvements juste avant la clôture ;
- nombres ronds : montants « fabriqués » (multiples de 1000) ;
- doublons : montants strictement identiques répétés ;
- contrepassations : paires débit/crédit exactement opposées sur un même compte.
"""
from __future__ import annotations

from collections import Counter
from datetime import timedelta

from app.services.fec_service import EcritureFEC, parser_ecritures

# Journaux d'à-nouveaux (soldes d'ouverture) exclus de l'analyse temporelle.
_JOURNAUX_AN = {"AN", "ANO", "ANOUV", "ANOUVEAUX", "AN0"}


def _structuration(ecritures: list[EcritureFEC], seuil: float, bande: float = 0.10) -> dict:
    bas = seuil * (1 - bande)
    vises = [e for e in ecritures if bas <= e.montant < seuil]
    return {
        "seuil": seuil,
        "borne_basse": round(bas, 2),
        "nb": len(vises),
        "total": round(sum(e.montant for e in vises), 2),
        "exemples": [(e.compte, round(e.montant, 2)) for e in vises[:5]],
    }


def _window_dressing(ecritures: list[EcritureFEC], cloture, jours: int = 15) -> dict:
    dated = [e for e in ecritures
             if e.date is not None and e.journal.upper() not in _JOURNAUX_AN]
    total = sum(e.montant for e in dated)
    if cloture is None or total <= 0:
        return {"applicable": False}
    debut = cloture - timedelta(days=jours)
    fenetre = [e for e in dated if debut <= e.date <= cloture]
    part = sum(e.montant for e in fenetre) / total
    return {
        "applicable": True,
        "jours": jours,
        "part": round(part, 4),
        "nb_fenetre": len(fenetre),
        "total_fenetre": round(sum(e.montant for e in fenetre), 2),
        "suspicion": part > 0.30,
    }


def _nombres_ronds(ecritures: list[EcritureFEC]) -> dict:
    montants = [e.montant for e in ecritures if e.montant]
    n = len(montants)
    ronds = sum(1 for m in montants if m >= 1000 and round(m) % 1000 == 0)
    return {"nb": ronds, "part": round(ronds / n, 4) if n else 0.0}


def _doublons(ecritures: list[EcritureFEC]) -> dict:
    compte = Counter(round(e.montant, 2) for e in ecritures if e.montant)
    dup = {v: c for v, c in compte.items() if c > 1}
    return {"nb": len(dup), "top": sorted(dup.items(), key=lambda x: -x[1])[:5]}


def _contrepassations(ecritures: list[EcritureFEC]) -> dict:
    # Paires (compte, +m) et (compte, -m) : débit et crédit opposés de même montant.
    positifs = Counter((e.compte, round(e.debit, 2)) for e in ecritures if e.debit)
    negatifs = Counter((e.compte, round(e.credit, 2)) for e in ecritures if e.credit)
    paires = sum(min(positifs[k], negatifs[k]) for k in positifs if k in negatifs and k[1] > 0)
    return {"nb": paires}


def _tva_coherence(ecritures: list[EcritureFEC]) -> dict:
    """Taux de TVA collectée implicite (TVA collectée / CA) vs bande plausible.

    Signal de cohérence à justifier : un taux hors bande peut traduire des ventes
    à taux réduit, des exports/exonérations… ou une TVA sous-déclarée. Jamais une
    conclusion — oriente le rapprochement avec les déclarations de TVA.
    """
    ca = sum(e.credit - e.debit for e in ecritures if e.compte.startswith("70"))
    tva = sum(e.credit - e.debit for e in ecritures if e.compte.startswith("4457"))
    if ca <= 0 or tva <= 0:
        return {"applicable": False, "ca": round(ca, 2), "tva_collectee": round(tva, 2)}
    taux = tva / ca
    plausible = 0.01 <= taux <= 0.22   # de 2,1 % (super-réduit) à 20 % + marge
    return {
        "applicable": True,
        "ca": round(ca, 2),
        "tva_collectee": round(tva, 2),
        "taux_implicite": round(taux, 4),
        "plausible": plausible,
    }


def _tiers(ecritures: list[EcritureFEC], seuil_eleve: float = 10000.0) -> dict:
    """Signaux sur les tiers (auxiliaires FEC) — fournisseurs et personnel.

    Couvre la partie FEC-exploitable des détecteurs « fournisseurs fictifs » et
    « salariés fictifs » : concentration, montants exclusivement ronds, tiers à
    occurrence unique avec montant élevé, salaires identiques partagés. La
    détection complète des salariés fictifs exige des données paie/DSN externes.
    """
    # Fournisseurs : auxiliaires des comptes 401x (montants crédités = achats).
    fournisseurs: dict[str, list[float]] = {}
    for e in ecritures:
        if e.compte.startswith("401") and e.aux_num and e.credit > 0:
            fournisseurs.setdefault(e.aux_num, []).append(e.credit)
    totaux = {aux: sum(m) for aux, m in fournisseurs.items()}
    total_achats = sum(totaux.values())
    top_part = (max(totaux.values()) / total_achats) if total_achats > 0 else 0.0
    exclusifs_ronds = [aux for aux, ms in fournisseurs.items()
                       if sum(ms) >= 3000 and all(round(m) % 1000 == 0 for m in ms)]
    uniques_eleves = [aux for aux, ms in fournisseurs.items()
                      if len(ms) == 1 and ms[0] >= seuil_eleve]

    # Personnel : auxiliaires des comptes 421x (salaires nets versés).
    salaries: dict[str, list[float]] = {}
    for e in ecritures:
        if e.compte.startswith("421") and e.aux_num and e.credit > 0:
            salaries.setdefault(e.aux_num, []).append(round(e.credit, 2))
    par_montant: Counter = Counter()
    for aux, ms in salaries.items():
        for m in set(ms):
            par_montant[m] += 1
    montants_partages = sum(1 for m, n in par_montant.items() if n >= 3)

    return {
        "fournisseurs_nb": len(fournisseurs),
        "fournisseurs_top_part": round(top_part, 4),
        "fournisseurs_ronds": exclusifs_ronds[:5],
        "fournisseurs_ronds_nb": len(exclusifs_ronds),
        "fournisseurs_uniques_eleves": uniques_eleves[:5],
        "fournisseurs_uniques_eleves_nb": len(uniques_eleves),
        "salaries_nb": len(salaries),
        "salaires_identiques_partages_nb": montants_partages,
    }


def analyser_ecritures(ecritures: list[EcritureFEC], cloture=None,
                       seuil_structuration: float = 10000.0) -> dict:
    """Applique tous les détecteurs et retourne un tableau de signaux."""
    return {
        "n": len(ecritures),
        "structuration": _structuration(ecritures, seuil_structuration),
        "window_dressing": _window_dressing(ecritures, cloture),
        "nombres_ronds": _nombres_ronds(ecritures),
        "doublons": _doublons(ecritures),
        "contrepassations": _contrepassations(ecritures),
        "tva": _tva_coherence(ecritures),
        "tiers": _tiers(ecritures, seuil_structuration),
    }


def signaux_res(res: dict) -> tuple[int, list[str]]:
    """Signaux d'alerte déclenchés à partir du résultat live (dict). NEP 240."""
    libelles: list[str] = []
    if res.get("structuration", {}).get("nb"):
        libelles.append("structuration")
    if res.get("window_dressing", {}).get("suspicion"):
        libelles.append("window dressing")
    tva = res.get("tva", {})
    if tva.get("applicable") and not tva.get("plausible", True):
        libelles.append("cohérence TVA")
    tiers = res.get("tiers", {})
    if tiers.get("fournisseurs_top_part", 0) > 0.5:
        libelles.append("concentration fournisseur")
    if tiers.get("fournisseurs_ronds_nb"):
        libelles.append("fournisseurs à montants ronds")
    if tiers.get("fournisseurs_uniques_eleves_nb"):
        libelles.append("fournisseur à écriture unique élevée")
    if tiers.get("salaires_identiques_partages_nb"):
        libelles.append("salaires nets identiques")
    return len(libelles), libelles


def signaux_orm(ff) -> tuple[int, list[str]]:
    """Mêmes signaux, calculés sur le résultat persisté (objet ORM)."""
    libelles: list[str] = []
    if ff.structuration_nb:
        libelles.append("structuration")
    if ff.window_suspicion:
        libelles.append("window dressing")
    if ff.tva_applicable and not ff.tva_plausible:
        libelles.append("cohérence TVA")
    if ff.tiers_top_part > 0.5:
        libelles.append("concentration fournisseur")
    if ff.tiers_ronds_nb:
        libelles.append("fournisseurs à montants ronds")
    if ff.tiers_uniques_eleves_nb:
        libelles.append("fournisseur à écriture unique élevée")
    if getattr(ff, "tiers_salaires_partages_nb", 0):
        libelles.append("salaires nets identiques")
    return len(libelles), libelles


def analyser_fec(contenu: str, cloture=None, seuil_structuration: float = 10000.0) -> dict:
    """Parse un FEC et applique les détecteurs de fraude."""
    return analyser_ecritures(parser_ecritures(contenu), cloture, seuil_structuration)


def enregistrer(db, mission_id: int, res: dict, fichier: str = "") -> None:
    """Persiste (remplace) le dernier résultat d'analyse fraude FEC de la mission."""
    from app.models.fraude_fec import FraudeFecResultat
    db.query(FraudeFecResultat).filter_by(mission_id=mission_id).delete()
    wd = res.get("window_dressing", {})
    tva = res.get("tva", {})
    db.add(FraudeFecResultat(
        mission_id=mission_id,
        n_ecritures=res.get("n", 0),
        seuil_structuration=res.get("structuration", {}).get("seuil", 10000.0),
        structuration_nb=res.get("structuration", {}).get("nb", 0),
        window_part=wd.get("part", 0.0) if wd.get("applicable") else 0.0,
        window_applicable=bool(wd.get("applicable")),
        window_suspicion=bool(wd.get("suspicion")),
        nombres_ronds_nb=res.get("nombres_ronds", {}).get("nb", 0),
        doublons_nb=res.get("doublons", {}).get("nb", 0),
        contrepassations_nb=res.get("contrepassations", {}).get("nb", 0),
        tva_applicable=bool(tva.get("applicable")),
        tva_taux_implicite=tva.get("taux_implicite", 0.0) if tva.get("applicable") else 0.0,
        tva_plausible=bool(tva.get("plausible", True)),
        tiers_fournisseurs_nb=res.get("tiers", {}).get("fournisseurs_nb", 0),
        tiers_top_part=res.get("tiers", {}).get("fournisseurs_top_part", 0.0),
        tiers_ronds_nb=res.get("tiers", {}).get("fournisseurs_ronds_nb", 0),
        tiers_uniques_eleves_nb=res.get("tiers", {}).get("fournisseurs_uniques_eleves_nb", 0),
        tiers_salaires_partages_nb=res.get("tiers", {}).get("salaires_identiques_partages_nb", 0),
        fichier=fichier[:255],
    ))
    db.commit()
