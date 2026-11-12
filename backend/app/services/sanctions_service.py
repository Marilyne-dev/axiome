"""Screening de sanctions — fournisseur par fichier local, prêt à brancher.

Fonctionnement réel :
- si un fichier `storage/sanctions/liste.csv` est présent (colonnes : nom[,type,
  programme,source]), il est utilisé comme référentiel de screening ;
- sinon, une petite liste de démonstration intégrée sert de repli, clairement signalé.

Les flux OFFICIELS (UE, OFAC, ONU) ne sont PAS connectés : ils nécessitent des
abonnements/API et une gouvernance de mise à jour. L'interface ci-dessous est conçue
pour les accueillir (il suffit d'alimenter le fichier, ou d'ajouter un fournisseur).
"""
from __future__ import annotations

import csv
import unicodedata
from pathlib import Path

from app.core.config import settings

_DEMO = [
    {"nom": "John Doe Sanctionne", "type": "personne", "programme": "DEMO", "source": "demo"},
    {"nom": "Societe Ecran XYZ", "type": "entite", "programme": "DEMO", "source": "demo"},
]


def _chemin_liste() -> Path:
    return Path(settings.storage_dir) / "sanctions" / "liste.csv"


def _normaliser(nom: str) -> str:
    s = unicodedata.normalize("NFKD", nom or "").encode("ascii", "ignore").decode()
    return " ".join(s.lower().split())


def _charger_fichier() -> list[dict] | None:
    chemin = _chemin_liste()
    if not chemin.exists():
        return None
    entrees: list[dict] = []
    with chemin.open(encoding="utf-8", newline="") as f:
        for ligne in csv.DictReader(f):
            nom = (ligne.get("nom") or "").strip()
            if nom:
                entrees.append({
                    "nom": nom, "type": (ligne.get("type") or "").strip(),
                    "programme": (ligne.get("programme") or "").strip(),
                    "source": (ligne.get("source") or "fichier").strip(),
                })
    return entrees


def _liste() -> tuple[list[dict], str]:
    """Retourne (entrées, origine) : 'fichier' si liste.csv présente, sinon 'demo'."""
    fichier = _charger_fichier()
    if fichier is not None:
        return fichier, "fichier"
    return list(_DEMO), "demo"


def source_active() -> dict:
    entrees, origine = _liste()
    return {"origine": origine, "entrees": len(entrees), "chemin": str(_chemin_liste())}


def screener(nom: str) -> dict:
    """Compare un nom au référentiel de sanctions (correspondance normalisée bidirectionnelle)."""
    cible = _normaliser(nom)
    entrees, origine = _liste()
    correspondances = []
    if cible:
        for e in entrees:
            ref = _normaliser(e["nom"])
            if ref and (ref in cible or cible in ref):
                correspondances.append(e)
    return {
        "nom": nom, "match": bool(correspondances),
        "correspondances": correspondances, "source": origine,
        "note": "Résultat indicatif — à valider par le correspondant LCB-FT.",
    }
