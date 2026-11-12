"""Contenu normatif par référentiel (Phase 7, Modules 21-23).

Données de référence réelles et vérifiables :
- normes d'audit applicables par zone ;
- table de correspondance NEP (France) ↔ ISA (international) ;
- structure des plans de comptes PCG et SYSCOHADA révisé.

Ce module fournit du CONTENU de référence exploité par les vues et les rapports.
Il ne remplace pas les textes officiels (CNCC, IAASB, OHADA) : il les cartographie.
"""
from __future__ import annotations

# Classes du Plan Comptable Général (France).
PCG_CLASSES: list[tuple[str, str]] = [
    ("1", "Comptes de capitaux"),
    ("2", "Comptes d'immobilisations"),
    ("3", "Comptes de stocks et en-cours"),
    ("4", "Comptes de tiers"),
    ("5", "Comptes financiers"),
    ("6", "Comptes de charges"),
    ("7", "Comptes de produits"),
    ("8", "Comptes spéciaux"),
]

# Classes du SYSCOHADA révisé (OHADA) — 9 classes.
SYSCOHADA_CLASSES: list[tuple[str, str]] = [
    ("1", "Comptes de ressources durables"),
    ("2", "Comptes d'actif immobilisé"),
    ("3", "Comptes de stocks"),
    ("4", "Comptes de tiers"),
    ("5", "Comptes de trésorerie"),
    ("6", "Comptes de charges des activités ordinaires"),
    ("7", "Comptes de produits des activités ordinaires"),
    ("8", "Comptes des autres charges et produits (HAO)"),
    ("9", "Engagements hors bilan et comptabilité analytique"),
]

# Correspondance NEP (CNCC, France) ↔ ISA (IAASB, international).
CORRESPONDANCE_NEP_ISA: list[tuple[str, str, str]] = [
    ("Objectifs généraux de l'auditeur", "NEP 200", "ISA 200"),
    ("Fraude", "NEP 240", "ISA 240"),
    ("Planification", "NEP 300", "ISA 300"),
    ("Connaissance de l'entité et évaluation des risques", "NEP 315", "ISA 315"),
    ("Caractère significatif (seuil)", "NEP 320", "ISA 320"),
    ("Réponses aux risques évalués", "NEP 330", "ISA 330"),
    ("Éléments probants", "NEP 500", "ISA 500"),
    ("Demandes de confirmation externes", "NEP 505", "ISA 505"),
    ("Soldes d'ouverture (première mission)", "NEP 510", "ISA 510"),
    ("Procédures analytiques", "NEP 520", "ISA 520"),
    ("Sélection des éléments (sondages)", "NEP 530", "ISA 530"),
    ("Estimations comptables", "NEP 540", "ISA 540"),
    ("Événements postérieurs à la clôture", "NEP 560", "ISA 560"),
    ("Continuité d'exploitation", "NEP 570", "ISA 570"),
    ("Déclarations de la direction", "NEP 580", "ISA 580"),
    ("Audit des comptes de groupe", "NEP 600", "ISA 600"),
    ("Fondement de l'opinion et rapport", "NEP 700", "ISA 700"),
    ("Opinions modifiées", "NEP 705", "ISA 705"),
]

REFERENTIELS_CONTENU: dict[str, dict] = {
    "PCG_FR": {
        "libelle": "Plan Comptable Général (France)",
        "zone": "France",
        "normes_comptables": "PCG (règlement ANC)",
        "normes_audit": ["NEP — Normes d'Exercice Professionnel (CNCC)"],
        "classes": PCG_CLASSES,
        "note": "Certification légale des comptes selon les NEP homologuées.",
    },
    "IFRS": {
        "libelle": "Normes internationales IFRS",
        "zone": "International",
        "normes_comptables": "IFRS (IASB)",
        "normes_audit": ["ISA — International Standards on Auditing (IAASB)"],
        "classes": [],  # les IFRS ne reposent pas sur un plan de comptes normalisé
        "note": "Présentation selon IAS 1 ; audit conduit selon les ISA.",
    },
    "SYSCOHADA_OHADA": {
        "libelle": "SYSCOHADA révisé (OHADA)",
        "zone": "Afrique — 17 États membres de l'OHADA",
        "normes_comptables": "SYSCOHADA révisé (Acte uniforme OHADA)",
        "normes_audit": ["ISA", "Acte uniforme OHADA relatif au droit des sociétés"],
        "classes": SYSCOHADA_CLASSES,
        "note": "Système comptable OHADA révisé (applicable depuis 2018).",
    },
}


def contenu_referentiel(referentiel: str) -> dict | None:
    """Retourne le contenu normatif d'un référentiel, ou None s'il est inconnu."""
    return REFERENTIELS_CONTENU.get(referentiel)


def normes_audit(referentiel: str) -> list[str]:
    """Liste des normes d'audit applicables au référentiel (repli : NEP)."""
    contenu = REFERENTIELS_CONTENU.get(referentiel)
    return contenu["normes_audit"] if contenu else ["NEP — Normes d'Exercice Professionnel (CNCC)"]
