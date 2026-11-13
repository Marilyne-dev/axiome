"""Traitements lourds en tâche de fond (génération de gros classeurs, etc.).

Principe : la requête HTTP rend la main tout de suite avec un identifiant de tâche ; le travail
s'exécute dans un thread du processus, le résultat est écrit sur disque (volume partagé), et le
front interroge GET /taches/{id} jusqu'à l'état « termine ».

L'état est stocké dans des fichiers JSON : il est donc lisible depuis n'importe quel worker qui
partage le même volume `storage`. Limite connue : si le processus qui exécute la tâche s'arrête
(redémarrage), la tâche reste « en_cours » — elle est alors déclarée « echec » après `DELAI_MAX_S`.
Pour de très gros volumes, remplacer ce module par une file dédiée (RQ/Celery) en gardant la même API.
"""
from __future__ import annotations

import json
import os
import secrets
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable

DELAI_MAX_S = 30 * 60
CONSERVATION_S = 24 * 3600
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="axiome-tache")
_base: Path | None = None


def configurer(dossier: str | Path) -> None:
    """Fixe le dossier des tâches (tests) ; par défaut `<storage_dir>/taches`."""
    global _base
    _base = Path(dossier)
    _base.mkdir(parents=True, exist_ok=True)


def _dossier() -> Path:
    global _base
    if _base is None:
        from app.core.config import settings  # import tardif : module testable sans configuration
        configurer(Path(settings.storage_dir) / "taches")
    return _base  # type: ignore[return-value]


def _ecrire_etat(tid: str, etat: dict) -> None:
    chemin = _dossier() / f"{tid}.json"
    tmp = chemin.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(etat, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, chemin)  # écriture atomique


def _lire_etat(tid: str) -> dict | None:
    if not tid.isalnum():  # empêche toute traversée de chemin
        return None
    chemin = _dossier() / f"{tid}.json"
    if not chemin.exists():
        return None
    try:
        return json.loads(chemin.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _nettoyer() -> None:
    limite = time.time() - CONSERVATION_S
    for p in _dossier().glob("*"):
        try:
            if p.stat().st_mtime < limite:
                p.unlink()
        except OSError:
            pass


def lancer(travail: Callable[[], tuple[bytes, str, str]], proprietaire: int, libelle: str) -> str:
    """Démarre `travail()` en arrière-plan. `travail` renvoie (contenu, nom_fichier, type_mime)."""
    _nettoyer()
    tid = secrets.token_hex(12)
    _ecrire_etat(tid, {"id": tid, "statut": "en_cours", "proprietaire": proprietaire,
                       "libelle": libelle, "debut": time.time()})

    def _run() -> None:
        try:
            contenu, nom, mime = travail()
            (_dossier() / f"{tid}.bin").write_bytes(contenu)
            _ecrire_etat(tid, {"id": tid, "statut": "termine", "proprietaire": proprietaire,
                               "libelle": libelle, "fichier": nom, "mime": mime,
                               "taille": len(contenu), "fin": time.time()})
        except Exception as exc:  # noqa: BLE001 — l'erreur est restituée au demandeur
            _ecrire_etat(tid, {"id": tid, "statut": "echec", "proprietaire": proprietaire,
                               "libelle": libelle, "erreur": str(exc)[:500], "fin": time.time()})

    _executor.submit(_run)
    return tid


def etat(tid: str, proprietaire: int | None = None, superadmin: bool = False) -> dict | None:
    """État public de la tâche, ou None si inconnue / appartenant à un autre utilisateur."""
    e = _lire_etat(tid)
    if e is None:
        return None
    if not superadmin and proprietaire is not None and e.get("proprietaire") != proprietaire:
        return None
    if e["statut"] == "en_cours" and time.time() - e.get("debut", 0) > DELAI_MAX_S:
        e = {**e, "statut": "echec", "erreur": "Délai dépassé (tâche interrompue)."}
    return {k: v for k, v in e.items() if k != "proprietaire"}


def resultat(tid: str, proprietaire: int | None = None, superadmin: bool = False) -> tuple[bytes, str, str] | None:
    e = etat(tid, proprietaire, superadmin)
    if not e or e["statut"] != "termine":
        return None
    return (_dossier() / f"{tid}.bin").read_bytes(), e["fichier"], e["mime"]
