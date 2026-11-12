"""Référentiel des cycles d'audit (correspondance CS_STANDARD Datayoyo → code cycle).

Aligné sur les feuilles maîtresses Datayoyo. Extensible : ajouter une entrée
suffit, sans toucher au moteur de génération.
"""
from __future__ import annotations

# code_cycle -> (libellé, ensemble de valeurs CS_STANDARD rattachées)
CYCLES: dict[str, dict] = {
    "TRESORERIE": {"libelle": "Trésorerie",
                   "cs": {"TRESORERIE", "RESULTAT FINANCIER"}},
    "EMPRUNTS": {"libelle": "Emprunts",
                 "cs": {"EMPRUNTS ET DETTES ASSIMILEES"}},
    "IMMO_CORP": {"libelle": "Immobilisations corporelles et incorporelles",
                  "cs": {"IMMOBILISATIONS CORPORELLES", "IMMOBILISATIONS INCORPORELLES"}},
    "IMMO_FI": {"libelle": "Immobilisations financières",
                "cs": {"IMMOBILISATIONS FINANCIERES", "VNC ET PROD. DES IMMOS FINANCIERES CEDEES"}},
    "STOCKS": {"libelle": "Stocks", "cs": {"STOCKS"}},
    "CLIENTS": {"libelle": "Clients, subventions et produits",
                "cs": {"CLIENTS ET COMPTES RATTACHES"}},
    "FOURNISSEURS": {"libelle": "Fournisseurs",
                     "cs": {"FOURNISSEURS ET COMPTES RATTACHES"}},
    "FONDS_PROPRES": {"libelle": "Fonds propres", "cs": {"CAPITAUX PROPRES"}},
    "PRC": {"libelle": "Provisions pour risques et charges",
            "cs": {"PROVISIONS POUR RISQUES ET CHARGES"}},
    "PERSONNEL": {"libelle": "Personnel", "cs": {"PERSONNEL ET COMPTES RATTACHES"}},
    "IMPOTS": {"libelle": "Impôts et taxes", "cs": {"ETAT ET AUTRES COLLECTIVITES"}},
    "AFFILIES": {"libelle": "Affiliés et partenaires", "cs": {"COMPTES DE GROUPE ET ASSOCIES"}},
    "AUTRES": {"libelle": "Autres comptes", "cs": {"AUTRES COMPTES"}},
}


def cycle_pour_cs(cs_standard: str) -> str:
    """Retourne le code cycle correspondant à un CS_STANDARD (défaut : AUTRES)."""
    cs_norm = (cs_standard or "").strip().upper()
    for code, meta in CYCLES.items():
        if cs_norm in meta["cs"]:
            return code
    return "AUTRES"


# CS_STANDARD représentatif de chaque cycle (membre de son ensemble « cs »),
# utilisé pour réaffecter manuellement une ligne à un cycle donné.
CS_REPRESENTATIF: dict[str, str] = {
    "TRESORERIE": "TRESORERIE",
    "EMPRUNTS": "EMPRUNTS ET DETTES ASSIMILEES",
    "IMMO_CORP": "IMMOBILISATIONS CORPORELLES",
    "IMMO_FI": "IMMOBILISATIONS FINANCIERES",
    "STOCKS": "STOCKS",
    "CLIENTS": "CLIENTS ET COMPTES RATTACHES",
    "FOURNISSEURS": "FOURNISSEURS ET COMPTES RATTACHES",
    "FONDS_PROPRES": "CAPITAUX PROPRES",
    "PRC": "PROVISIONS POUR RISQUES ET CHARGES",
    "PERSONNEL": "PERSONNEL ET COMPTES RATTACHES",
    "IMPOTS": "ETAT ET AUTRES COLLECTIVITES",
    "AFFILIES": "COMPTES DE GROUPE ET ASSOCIES",
    "AUTRES": "AUTRES COMPTES",
}


def cs_representatif(code_cycle: str) -> str:
    """CS_STANDARD canonique d'un code cycle (pour réaffectation manuelle)."""
    return CS_REPRESENTATIF.get(code_cycle, "AUTRES COMPTES")


def libelle_cycle(code: str) -> str:
    return CYCLES.get(code, {}).get("libelle", code.title())
