"""Service de cartographie des risques : heat map et priorisation automatique."""
from __future__ import annotations

from collections.abc import Iterable

from app.models.audit import RiskItem


def niveau(score: int) -> str:
    """Classe un score (proba × impact, 1..25) en faible/modéré/élevé/critique."""
    if score >= 16:
        return "critique"
    if score >= 9:
        return "eleve"
    if score >= 4:
        return "modere"
    return "faible"


def heatmap(risques: Iterable[RiskItem]) -> dict:
    """Agrège les risques en une matrice 5×5 (impact × probabilité) + comptage par niveau."""
    matrice = [[0] * 5 for _ in range(5)]  # [impact-1][proba-1]
    niveaux = {"faible": 0, "modere": 0, "eleve": 0, "critique": 0}
    for r in risques:
        i = min(max(r.impact, 1), 5) - 1
        p = min(max(r.probabilite, 1), 5) - 1
        matrice[i][p] += 1
        niveaux[niveau(r.score)] += 1
    return {"matrice": matrice, "par_niveau": niveaux}


def prioriser(risques: list[RiskItem]) -> list[RiskItem]:
    """Trie les risques par score décroissant (priorisation automatique)."""
    return sorted(risques, key=lambda r: r.score, reverse=True)
