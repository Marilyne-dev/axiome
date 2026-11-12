"""Module 27 — Calcul des seuils (signification, planification, remontée).

Seuil de signification : on retient la valeur la plus faible parmi les bases
retenues (résultat net, chiffre d'affaires, capitaux propres), chaque base
ayant un taux paramétrable. Seuil de planification = % du seuil de signification.
Seuil de remontée = % du seuil de signification. Tous paramétrables.
"""
from __future__ import annotations

from dataclasses import dataclass

# Fourchettes usuelles par défaut (paramétrables par l'utilisateur).
TAUX_DEFAUT = {
    "resultat_net": 0.05,      # 5 % du résultat net courant
    "chiffre_affaires": 0.01,  # 1 % du CA (fourchette 1-2 %)
    "capitaux_propres": 0.01,  # 1 % des capitaux propres
}
RATIO_PLANIFICATION_DEFAUT = 0.75   # 50-75 % du seuil de signification
RATIO_REMONTEE_DEFAUT = 0.05        # 5-10 % du seuil de signification


@dataclass
class ResultatSeuils:
    seuil_signification: float
    seuil_planification: float
    seuil_remontee: float
    base_retenue: str
    details: dict


def calculer(
    bases: dict[str, float],
    taux: dict[str, float] | None = None,
    ratio_planification: float = RATIO_PLANIFICATION_DEFAUT,
    ratio_remontee: float = RATIO_REMONTEE_DEFAUT,
) -> ResultatSeuils:
    """Calcule les trois seuils à partir des bases financières fournies.

    `bases` : {'resultat_net': ..., 'chiffre_affaires': ..., 'capitaux_propres': ...}
    Retient la valeur la plus faible (en valeur absolue) comme seuil de signification.
    """
    taux = {**TAUX_DEFAUT, **(taux or {})}
    candidats: dict[str, float] = {}
    for base, montant in bases.items():
        if base in taux and montant:
            candidats[base] = abs(float(montant)) * taux[base]

    if not candidats:
        return ResultatSeuils(0.0, 0.0, 0.0, "", {})

    base_retenue = min(candidats, key=candidats.get)
    seuil_signif = round(candidats[base_retenue], 2)
    return ResultatSeuils(
        seuil_signification=seuil_signif,
        seuil_planification=round(seuil_signif * ratio_planification, 2),
        seuil_remontee=round(seuil_signif * ratio_remontee, 2),
        base_retenue=base_retenue,
        details={b: round(v, 2) for b, v in candidats.items()},
    )
