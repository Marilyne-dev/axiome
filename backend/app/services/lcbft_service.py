"""Module 13 bis — LCB-FT : classification du risque et screening PPE/sanctions.

Aligné sur l'approche par les risques (GAFI/FATF). Le screening et le score de
risque sont des AIDES : le correspondant LCB-FT décide et motive. Les données
sont confidentielles (accès restreint + journalisé).
"""
from __future__ import annotations

import unicodedata

from app.services import sanctions_service

# Liste PPE de démonstration (à remplacer par un flux officiel PPE tenu à jour).
_PPE_DEMO = {"personne politiquement exposee demo"}


def _normaliser(nom: str) -> str:
    """Minuscule, sans accents ni ponctuation superflue (comparaison robuste)."""
    s = unicodedata.normalize("NFKD", nom or "").encode("ascii", "ignore").decode()
    return " ".join(s.lower().split())


def screening(nom: str) -> dict:
    """Compare un nom aux référentiels de sanctions (fichier/démo) et PPE."""
    res_sanctions = sanctions_service.screener(nom)
    hit_sanctions = res_sanctions["match"]
    hit_ppe = _normaliser(nom) in _PPE_DEMO
    return {
        "nom": nom,
        "match_sanctions": hit_sanctions,
        "correspondances": res_sanctions["correspondances"],
        "source_sanctions": res_sanctions["source"],
        "match_ppe": hit_ppe,
        "vigilance": "renforcee" if (hit_sanctions or hit_ppe) else "standard",
        "note": "Résultat indicatif — à valider par le correspondant LCB-FT.",
    }


def classifier_risque(
    *, pays_a_risque: bool = False, activite_especes: bool = False,
    ppe: bool = False, structure_complexe: bool = False,
    relation_a_distance: bool = False,
) -> dict:
    """Classe le risque LCB-FT (faible/standard/élevé) par pondération de facteurs."""
    score = sum([
        2 if pays_a_risque else 0,
        2 if activite_especes else 0,
        4 if ppe else 0,   # une PPE déclenche seule la vigilance renforcée (GAFI)
        1 if structure_complexe else 0,
        1 if relation_a_distance else 0,
    ])
    niveau = "eleve" if score >= 4 else ("standard" if score >= 2 else "faible")
    return {"score": score, "niveau_risque": niveau,
            "vigilance": {"faible": "allegee", "standard": "normale", "eleve": "renforcee"}[niveau]}
