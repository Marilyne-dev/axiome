"""Module 6 — Analyse financière : agrégats de structure et ratios.

Calculés depuis la balance importée (LigneBalance) par regroupement des racines
de comptes PCG. Ce sont des indicateurs standard (FRNG, BFR, trésorerie nette,
ratios de structure et de liquidité) — une aide à l'analyse, à recouper avec la
liasse. Le signe des soldes suit la convention de la balance importée ; les
agrégats de masse utilisent la valeur absolue par nature de compte.
"""
from __future__ import annotations

from collections.abc import Iterable

from app.models.balance import LigneBalance


def _somme(lignes: Iterable[LigneBalance], prefixes: tuple[str, ...], champ: str = "solde_n") -> float:
    """Somme (en valeur absolue) des soldes des comptes commençant par un préfixe."""
    total = 0.0
    for lb in lignes:
        if lb.compte.startswith(prefixes):
            total += abs(getattr(lb, champ))
    return round(total, 2)


def agregats(lignes: list[LigneBalance], champ: str = "solde_n") -> dict:
    """Calcule les masses bilancielles à partir des racines de comptes PCG."""
    capitaux_propres = _somme(lignes, ("10", "11", "12", "13", "14"), champ)
    provisions = _somme(lignes, ("15",), champ)
    dettes_financieres = _somme(lignes, ("16",), champ)
    immobilisations = _somme(lignes, ("20", "21", "22", "23", "26", "27", "28"), champ)
    stocks = _somme(lignes, ("31", "32", "33", "34", "35", "37"), champ)
    creances_clients = _somme(lignes, ("41",), champ)
    dettes_fournisseurs = _somme(lignes, ("40",), champ)
    dettes_fisc_soc = _somme(lignes, ("42", "43", "44"), champ)
    tresorerie_actif = _somme(lignes, ("50", "51", "53"), champ)

    ressources_durables = round(capitaux_propres + provisions + dettes_financieres, 2)
    emplois_stables = immobilisations
    frng = round(ressources_durables - emplois_stables, 2)                 # fonds de roulement net global
    bfr = round((stocks + creances_clients) - (dettes_fournisseurs + dettes_fisc_soc), 2)
    tresorerie_nette = round(frng - bfr, 2)

    return {
        "capitaux_propres": capitaux_propres, "provisions": provisions,
        "dettes_financieres": dettes_financieres, "immobilisations": immobilisations,
        "stocks": stocks, "creances_clients": creances_clients,
        "dettes_fournisseurs": dettes_fournisseurs, "dettes_fisc_soc": dettes_fisc_soc,
        "tresorerie_actif": tresorerie_actif,
        "ressources_durables": ressources_durables, "emplois_stables": emplois_stables,
        "fonds_de_roulement_net_global": frng, "besoin_en_fonds_de_roulement": bfr,
        "tresorerie_nette": tresorerie_nette,
    }


def _ratio(num: float, den: float) -> float | None:
    return round(num / den, 3) if den else None


def ratios(lignes: list[LigneBalance]) -> dict:
    """Ratios financiers usuels dérivés des agrégats."""
    a = agregats(lignes)
    actif_circulant = a["stocks"] + a["creances_clients"] + a["tresorerie_actif"]
    dettes_ct = a["dettes_fournisseurs"] + a["dettes_fisc_soc"]
    total_actif = a["immobilisations"] + actif_circulant
    passif_total = a["capitaux_propres"] + a["provisions"] + a["dettes_financieres"] + dettes_ct
    return {
        "liquidite_generale": _ratio(actif_circulant, dettes_ct),
        "autonomie_financiere": _ratio(a["capitaux_propres"], passif_total),
        "taux_endettement": _ratio(a["dettes_financieres"], a["capitaux_propres"]),
        "couverture_immobilisations": _ratio(a["ressources_durables"], a["emplois_stables"]),
        "poids_bfr": _ratio(a["besoin_en_fonds_de_roulement"], total_actif),
    }


def analyse_complete(lignes: list[LigneBalance]) -> dict:
    """Retourne agrégats + ratios (N)."""
    return {"agregats": agregats(lignes), "ratios": ratios(lignes)}
