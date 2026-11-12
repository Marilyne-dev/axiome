"""Référentiel ESRS (CSRD) — structure et points de données.

Sous-ensemble représentatif et factuel des normes ESRS : les 10 thèmes topiques
(E1–E5, S1–S4, G1), assortis de quelques exigences de publication clés. Il ne
reproduit pas l'intégralité des ~1 000 points de données ESRS ; il fournit une
structure de travail auditée (double matérialité + couverture) à approfondir.

ESRS 1 (exigences générales) et ESRS 2 (informations générales) s'appliquent
toujours, indépendamment de la matérialité.
"""
from __future__ import annotations

PILIERS = {"E": "Environnement", "S": "Social", "G": "Gouvernance"}

# (code, libellé, pilier)
THEMES = [
    ("E1", "Changement climatique", "E"),
    ("E2", "Pollution", "E"),
    ("E3", "Eau et ressources marines", "E"),
    ("E4", "Biodiversité et écosystèmes", "E"),
    ("E5", "Utilisation des ressources et économie circulaire", "E"),
    ("S1", "Personnel de l'entreprise", "S"),
    ("S2", "Travailleurs de la chaîne de valeur", "S"),
    ("S3", "Communautés affectées", "S"),
    ("S4", "Consommateurs et utilisateurs finals", "S"),
    ("G1", "Conduite des affaires", "G"),
]

# code ESRS -> liste de points de données (code court, libellé)
DATAPOINTS = {
    "E1": [
        ("E1-1", "Plan de transition pour l'atténuation du changement climatique"),
        ("E1-4", "Cibles de réduction des émissions de GES"),
        ("E1-5", "Consommation d'énergie et mix énergétique"),
        ("E1-6", "Émissions brutes de GES (scopes 1, 2 et 3)"),
        ("E1-7", "Absorptions de GES et projets de compensation"),
    ],
    "E2": [
        ("E2-4", "Pollution de l'air, de l'eau et des sols"),
        ("E2-5", "Substances préoccupantes et extrêmement préoccupantes"),
    ],
    "E3": [
        ("E3-4", "Consommation d'eau"),
        ("E3-1", "Politiques relatives à l'eau et aux ressources marines"),
    ],
    "E4": [
        ("E4-5", "Indicateurs d'impact sur l'état des espèces et écosystèmes"),
        ("E4-2", "Politiques biodiversité ; sites proches de zones protégées"),
    ],
    "E5": [
        ("E5-4", "Flux de ressources entrants"),
        ("E5-5", "Flux de ressources sortants et déchets"),
    ],
    "S1": [
        ("S1-6", "Caractéristiques des salariés de l'entreprise"),
        ("S1-14", "Santé et sécurité au travail"),
        ("S1-16", "Rémunération et écart de rémunération femmes-hommes"),
        ("S1-17", "Incidents, plaintes et atteintes graves aux droits humains"),
    ],
    "S2": [
        ("S2-1", "Politiques relatives aux travailleurs de la chaîne de valeur"),
        ("S2-4", "Actions et diligence raisonnable en matière de droits humains"),
    ],
    "S3": [
        ("S3-1", "Politiques relatives aux communautés affectées"),
        ("S3-4", "Actions correctives et mécanismes de réclamation"),
    ],
    "S4": [
        ("S4-1", "Politiques relatives aux consommateurs et utilisateurs finals"),
        ("S4-4", "Sécurité et protection des consommateurs"),
    ],
    "G1": [
        ("G1-1", "Culture d'entreprise et politiques de conduite des affaires"),
        ("G1-3", "Prévention et détection de la corruption"),
        ("G1-4", "Cas de corruption avérés"),
        ("G1-6", "Pratiques de paiement (délais fournisseurs)"),
    ],
}

# Barème de matérialité (0..3)
ECHELLE = {0: "Nulle", 1: "Faible", 2: "Moyenne", 3: "Élevée"}
SEUIL_MATERIEL = 2  # matériel si impact OU financier >= seuil


def libelle_theme(code: str) -> str:
    for c, lib, _ in THEMES:
        if c == code:
            return lib
    return code


def pilier_theme(code: str) -> str:
    for c, _, p in THEMES:
        if c == code:
            return p
    return ""


def points_du_theme(code: str) -> list[tuple[str, str]]:
    return DATAPOINTS.get(code, [])


def est_materiel(impact: int, financier: int) -> bool:
    return max(impact or 0, financier or 0) >= SEUIL_MATERIEL
