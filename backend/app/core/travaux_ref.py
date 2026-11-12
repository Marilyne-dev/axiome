"""Objectifs et travaux à effectuer par cycle (texte des feuilles de travail)."""
from __future__ import annotations

OBJECTIF_GENERIQUE = (
    "Obtenir des éléments probants suffisants et appropriés sur les assertions "
    "d'audit relatives à ce cycle (existence, exhaustivité, exactitude, "
    "évaluation, séparation des exercices, présentation)."
)

TRAVAUX: dict[str, list[str]] = {
    "TRESORERIE": [
        "Identifier les comptes de banque à partir de la balance générale.",
        "Pour les comptes sélectionnés, réconcilier le solde comptable avec le relevé et l'état de rapprochement bancaire (ERB).",
        "Adresser les demandes de confirmation directe aux établissements bancaires.",
        "Contrôler les caisses et les valeurs mobilières de placement (VMP).",
    ],
    "EMPRUNTS": [
        "Réaliser le tableau de variation des emprunts (ouverture, souscriptions, remboursements, clôture).",
        "Sélectionner les emprunts à tester et effectuer le rapprochement avec les tableaux d'amortissement.",
        "Recalculer les intérêts d'emprunt et les intérêts courus non échus (ICNE).",
        "Confirmer les soldes auprès des établissements prêteurs.",
    ],
}


def travaux(code_cycle: str) -> list[str]:
    return TRAVAUX.get(code_cycle, [
        "Prendre connaissance des comptes du cycle à partir de la balance générale.",
        "Effectuer la revue analytique N / N-1 et justifier les variations significatives.",
        "Réaliser les tests de détail sur les postes significatifs.",
    ])
