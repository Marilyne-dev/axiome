"""Classification automatique d'un numéro de compte PCG vers un cycle d'audit.

Utilisé lors de l'import d'un FEC (qui ne fournit que des numéros de comptes) :
on en déduit un CS_STANDARD compatible avec `cycle_pour_cs`, de sorte que toute
la mécanique de regroupement par cycle fonctionne à l'identique.

Classification indicative selon le Plan Comptable Général ; elle reste éditable
(la colonne cycle des lignes de balance peut être ajustée par l'auditeur).
Les règles vont du préfixe le plus spécifique au plus général ; défaut : AUTRES.
"""
from __future__ import annotations

# (préfixe, CS_STANDARD) — ordre = priorité (préfixes longs d'abord).
_REGLES: tuple[tuple[str, str], ...] = (
    # Capitaux (classe 1)
    ("10", "CAPITAUX PROPRES"), ("11", "CAPITAUX PROPRES"), ("12", "CAPITAUX PROPRES"),
    ("13", "CAPITAUX PROPRES"), ("14", "CAPITAUX PROPRES"),
    ("15", "PROVISIONS POUR RISQUES ET CHARGES"),
    ("16", "EMPRUNTS ET DETTES ASSIMILEES"),
    ("17", "COMPTES DE GROUPE ET ASSOCIES"),
    ("18", "AUTRES COMPTES"),
    # Immobilisations (classe 2)
    ("26", "IMMOBILISATIONS FINANCIERES"), ("27", "IMMOBILISATIONS FINANCIERES"),
    ("20", "IMMOBILISATIONS CORPORELLES"), ("21", "IMMOBILISATIONS CORPORELLES"),
    ("22", "IMMOBILISATIONS CORPORELLES"), ("23", "IMMOBILISATIONS CORPORELLES"),
    ("28", "IMMOBILISATIONS CORPORELLES"), ("29", "IMMOBILISATIONS CORPORELLES"),
    # Stocks (classe 3)
    ("3", "STOCKS"),
    # Tiers (classe 4)
    ("40", "FOURNISSEURS ET COMPTES RATTACHES"),
    ("41", "CLIENTS ET COMPTES RATTACHES"),
    ("42", "PERSONNEL ET COMPTES RATTACHES"), ("43", "PERSONNEL ET COMPTES RATTACHES"),
    ("44", "ETAT ET AUTRES COLLECTIVITES"),
    ("45", "COMPTES DE GROUPE ET ASSOCIES"),
    ("46", "AUTRES COMPTES"), ("47", "AUTRES COMPTES"),
    ("48", "AUTRES COMPTES"), ("49", "AUTRES COMPTES"),
    # Financiers / trésorerie (classe 5)
    ("50", "TRESORERIE"), ("51", "TRESORERIE"), ("52", "TRESORERIE"), ("53", "TRESORERIE"),
    ("54", "TRESORERIE"), ("58", "TRESORERIE"), ("59", "TRESORERIE"),
    # Gestion (classes 6/7) — hors cycles de bilan → AUTRES
    ("6", "AUTRES COMPTES"), ("7", "AUTRES COMPTES"),
)


def cs_standard_pour_compte(compte: str) -> str:
    """Retourne le CS_STANDARD (compatible cycle_pour_cs) déduit du numéro de compte."""
    c = (compte or "").strip()
    for prefixe, cs in _REGLES:
        if c.startswith(prefixe):
            return cs
    return "AUTRES COMPTES"
