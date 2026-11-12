"""Service d'échantillonnage : calcul de taille indicatif (statistique / MUS).

Ces formules sont des AIDES à la décision de l'auditeur, jamais des décisions
automatiques ; l'auditeur ajuste selon son jugement professionnel (NEP 530 / ISA 530).
"""
from __future__ import annotations

import math

# Facteurs de fiabilité (Poisson, 0 erreur attendue) selon le niveau de confiance.
FACTEURS_FIABILITE = {0.80: 1.61, 0.90: 2.31, 0.95: 3.00, 0.99: 4.61}


def facteur(confiance: float) -> float:
    """Retourne le facteur de fiabilité le plus proche du niveau de confiance."""
    return FACTEURS_FIABILITE.get(round(confiance, 2), 3.0)


def taille_mus(valeur_population: float, seuil_tolerable: float,
               confiance: float = 0.95, erreur_attendue: float = 0.0) -> int:
    """Sondage en unités monétaires (MUS) : n ≈ (VP × RF) / (Tol − Att)."""
    denom = seuil_tolerable - erreur_attendue
    if valeur_population <= 0 or denom <= 0:
        return 0
    return max(1, math.ceil(valeur_population * facteur(confiance) / denom))


def taille_attributs(taux_tolerable: float, confiance: float = 0.95,
                     taux_attendu: float = 0.0) -> int:
    """Sondage en attributs (tests de contrôles) : n ≈ RF / (Tol − Att)."""
    denom = taux_tolerable - taux_attendu
    if denom <= 0:
        return 0
    return max(1, math.ceil(facteur(confiance) / denom))
