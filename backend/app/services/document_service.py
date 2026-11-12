"""Service GED : stockage des pièces sur disque + métadonnées en base.

Sécurité :
- le nom de fichier fourni n'est jamais utilisé pour construire le chemin sur disque
  (on génère un identifiant aléatoire) → pas de traversée de répertoire ;
- extensions restreintes aux formats d'audit courants ;
- taille plafonnée (settings.max_upload_mb), lecture en flux.
"""
from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.audit import Document

EXTENSIONS_AUTORISEES = {".pdf", ".xlsx", ".xls", ".docx", ".doc", ".csv",
                         ".png", ".jpg", ".jpeg", ".txt", ".xml"}


class UploadInvalide(ValueError):
    """Extension non autorisée ou fichier trop volumineux."""


def _dossier_mission(mission_id: int) -> Path:
    d = Path(settings.storage_dir) / "missions" / str(mission_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


def enregistrer(db: Session, mission_id: int, fichier: UploadFile,
                cycle_code: str = "", user_id: int | None = None) -> Document:
    """Enregistre une pièce : validation, écriture disque, ligne Document."""
    nom_original = Path(fichier.filename or "piece").name  # neutralise tout chemin
    ext = Path(nom_original).suffix.lower()
    if ext not in EXTENSIONS_AUTORISEES:
        raise UploadInvalide(f"Extension non autorisée : {ext or '(aucune)'}")

    cible = _dossier_mission(mission_id) / f"{uuid.uuid4().hex}{ext}"
    taille_max = settings.max_upload_mb * 1024 * 1024
    taille = 0
    with cible.open("wb") as sortie:
        while chunk := fichier.file.read(1024 * 1024):
            taille += len(chunk)
            if taille > taille_max:
                sortie.close()
                cible.unlink(missing_ok=True)
                raise UploadInvalide(f"Fichier trop volumineux (max {settings.max_upload_mb} Mo)")
            sortie.write(chunk)

    doc = Document(
        mission_id=mission_id, nom=nom_original,
        chemin=str(cible.relative_to(settings.storage_dir)),
        type_doc=ext.lstrip("."), content_type=fichier.content_type or "",
        taille=taille, cycle_code=cycle_code or "", uploaded_by=user_id,
    )
    db.add(doc); db.commit(); db.refresh(doc)
    return doc


def lister(db: Session, mission_id: int, cycle_code: str | None = None) -> list[Document]:
    q = db.query(Document).filter_by(mission_id=mission_id)
    if cycle_code:
        q = q.filter_by(cycle_code=cycle_code)
    return q.order_by(Document.created_at.desc()).all()


def chemin_absolu(doc: Document) -> Path:
    return Path(settings.storage_dir) / doc.chemin


def supprimer(db: Session, doc: Document) -> None:
    """Supprime la ligne et le fichier associé."""
    chemin_absolu(doc).unlink(missing_ok=True)
    db.delete(doc); db.commit()


def purger_mission(mission_id: int) -> None:
    """Supprime le répertoire de stockage d'une mission (utilitaire)."""
    d = Path(settings.storage_dir) / "missions" / str(mission_id)
    if d.exists():
        shutil.rmtree(d, ignore_errors=True)
