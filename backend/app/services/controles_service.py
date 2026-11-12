"""Contrôles automatiques déterministes sur la balance importée.

Aucune heuristique : uniquement des égalités comptables vérifiables.
Convention de bouclage (déjà utilisée par les tableaux de variation) :
    solde_n == solde_n1 + mvt_debit_n - mvt_credit_n
"""
from __future__ import annotations

from collections import Counter
from typing import Iterable, Protocol

_TOL = 0.01


class _Ligne(Protocol):
    compte: str
    libelle: str
    solde_n: float
    solde_n1: float
    mvt_debit_n: float
    mvt_credit_n: float


def _ecart_bouclage(l: _Ligne) -> float:
    return (l.solde_n or 0.0) - ((l.solde_n1 or 0.0) + (l.mvt_debit_n or 0.0) - (l.mvt_credit_n or 0.0))


def controler(lignes: Iterable[_Ligne]) -> dict:
    """Retourne {controles: [{libelle, statut, detail}], nb_anomalies}."""
    lignes = list(lignes)
    controles: list[dict] = []

    def ajouter(libelle: str, ok: bool, detail: str) -> None:
        controles.append({"libelle": libelle, "statut": "ok" if ok else "anomalie", "detail": detail})

    if not lignes:
        return {"controles": [{"libelle": "Balance", "statut": "anomalie",
                               "detail": "Aucune ligne importée."}], "nb_anomalies": 1}

    # 1. Équilibre des soldes N (Σ soldes débiteurs = Σ soldes créditeurs).
    total_solde = sum(l.solde_n or 0.0 for l in lignes)
    ajouter("Équilibre des soldes N", abs(total_solde) < _TOL,
            f"Σ soldes N = {round(total_solde, 2)} (attendu ≈ 0).")

    # 2. Équilibre des mouvements de l'exercice (Σ débit = Σ crédit).
    tot_deb = sum(l.mvt_debit_n or 0.0 for l in lignes)
    tot_cred = sum(l.mvt_credit_n or 0.0 for l in lignes)
    ajouter("Équilibre des mouvements", abs(tot_deb - tot_cred) < _TOL,
            f"Σ débit = {round(tot_deb, 2)} · Σ crédit = {round(tot_cred, 2)}.")

    # 3. Bouclage par compte (solde N = solde N-1 + débit - crédit).
    desequilibrees = [l for l in lignes if abs(_ecart_bouclage(l)) >= _TOL]
    ajouter("Bouclage ouverture → clôture", not desequilibrees,
            f"{len(desequilibrees)} compte(s) hors bouclage."
            + (f" Ex. : {desequilibrees[0].compte} (écart {round(_ecart_bouclage(desequilibrees[0]), 2)})."
               if desequilibrees else ""))

    # 4. Comptes en doublon.
    doublons = [c for c, n in Counter(l.compte for l in lignes if l.compte).items() if n > 1]
    ajouter("Unicité des comptes", not doublons,
            f"{len(doublons)} compte(s) en doublon." + (f" Ex. : {doublons[0]}." if doublons else ""))

    # 5. Libellés manquants.
    sans_libelle = [l for l in lignes if not (l.libelle or "").strip()]
    ajouter("Libellés renseignés", not sans_libelle,
            f"{len(sans_libelle)} compte(s) sans libellé.")

    nb = sum(1 for c in controles if c["statut"] == "anomalie")
    return {"controles": controles, "nb_anomalies": nb}
