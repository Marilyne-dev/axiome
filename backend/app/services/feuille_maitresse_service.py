"""Module 20 — Feuille Maîtresse par cycle (structure calée sur Datayoyo).

Colonnes réelles : Compte(s) comptable(s) | Solde N | Solde N-1 | Variation | % |
Référence de la procédure. Une ligne par compte du cycle + une ligne de total.

Le rattachement compte→cycle repose sur les racines du plan comptable (PCG).
C'est une donnée de PARAMÉTRAGE dépendant du référentiel (PCG ici) — SYSCOHADA
utiliserait d'autres racines. Ce n'est pas une règle fiscale codée en dur.
"""
from __future__ import annotations

from dataclasses import dataclass

# Racines PCG par cycle (paramétrable ; SYSCOHADA aurait sa propre table).
CYCLES_PCG: dict[str, tuple[str, ...]] = {
    "IMMOBILISATIONS": ("20", "21", "22", "23", "28", "29"),
    "IMMO_FINANCIERES": ("26", "27"),
    "STOCKS": ("31", "32", "33", "34", "35", "37", "39"),
    "CLIENTS": ("41", "416", "418", "491"),
    "TRESORERIE": ("50", "51", "53", "54", "58"),
    "FONDS_PROPRES": ("10", "11", "12", "13", "14"),
    "PROVISIONS": ("15",),
    "EMPRUNTS": ("16", "17", "519"),
    "FOURNISSEURS": ("40",),
    "PERSONNEL": ("42", "43"),
    "IMPOTS_TAXES": ("44", "63", "69"),
    "AUTRES_COMPTES": ("46", "47", "48"),
}


@dataclass
class LigneFM:
    compte: str
    libelle: str
    solde_n: float
    solde_n1: float

    @property
    def variation(self) -> float:
        return round(self.solde_n - self.solde_n1, 2)

    @property
    def pourcentage(self) -> float | None:
        if self.solde_n1 == 0:
            return None
        return round((self.solde_n - self.solde_n1) / abs(self.solde_n1), 4)


@dataclass
class FeuilleMaitresse:
    cycle: str
    lignes: list[LigneFM]
    total_n: float
    total_n1: float

    @property
    def total_variation(self) -> float:
        return round(self.total_n - self.total_n1, 2)


def _appartient(compte: str, racines: tuple[str, ...]) -> bool:
    return compte.startswith(racines)


def construire_fm(cycle_code: str, balance_n: dict[str, tuple[str, float]],
                  balance_n1: dict[str, tuple[str, float]] | None = None) -> FeuilleMaitresse:
    """Construit la FM d'un cycle à partir des balances N (et N-1) filtrées.

    balance_* : {compte: (libelle, solde)}.
    """
    racines = CYCLES_PCG.get(cycle_code.upper())
    if not racines:
        raise ValueError(f"Cycle inconnu pour le référentiel PCG : {cycle_code}")
    balance_n1 = balance_n1 or {}

    comptes = sorted(c for c in set(balance_n) | set(balance_n1) if _appartient(c, racines))
    lignes: list[LigneFM] = []
    for c in comptes:
        lib_n, solde_n = balance_n.get(c, ("", 0.0))
        lib_n1, solde_n1 = balance_n1.get(c, ("", 0.0))
        lignes.append(LigneFM(compte=c, libelle=lib_n or lib_n1, solde_n=solde_n, solde_n1=solde_n1))

    total_n = round(sum(l.solde_n for l in lignes), 2)
    total_n1 = round(sum(l.solde_n1 for l in lignes), 2)
    return FeuilleMaitresse(cycle=cycle_code.upper(), lignes=lignes, total_n=total_n, total_n1=total_n1)
