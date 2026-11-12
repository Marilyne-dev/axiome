"""Préparation des déclarations de soupçon TRACFIN — prêt à brancher.

Ce que fait RÉELLEMENT ce module :
- construit un export structuré (JSON) d'une déclaration de soupçon à partir du
  dossier LCB-FT et du client, et l'écrit dans une corbeille de sortie
  (`storage/tracfin_outbox/`) — artefact concret, prêt à être soumis.

Ce qu'il NE fait PAS (assumé) :
- il ne se connecte pas à la téléprocédure officielle ERMES/TRACFIN, qui exige un
  compte déclarant, un certificat et une convention. La transmission reste un acte
  effectué par le correspondant LCB-FT ; `marquer_transmise` enregistre sa confirmation.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.client import Client
from app.models.lcbft import DeclarationSoupcon, DossierLCBFT


def _corbeille() -> Path:
    d = Path(settings.storage_dir) / "tracfin_outbox"
    d.mkdir(parents=True, exist_ok=True)
    return d


def preparer_export(db: Session, declaration_id: int) -> dict:
    """Construit l'export d'une déclaration et l'écrit dans la corbeille de sortie."""
    decl = db.get(DeclarationSoupcon, declaration_id)
    if not decl:
        raise ValueError("Déclaration introuvable")
    dossier = db.get(DossierLCBFT, decl.dossier_id)
    client = db.get(Client, dossier.client_id) if dossier else None

    ref = decl.reference or f"DS-{decl.id}-{date.today():%Y%m%d}"
    decl.reference = ref

    payload = {
        "reference": ref,
        "date_preparation": date.today().isoformat(),
        "entite_declarante": settings.app_name,
        "client": {
            "raison_sociale": getattr(client, "raison_sociale", ""),
            "identifiant_legal": getattr(client, "identifiant_legal", ""),
            "pays": getattr(client, "pays", ""),
        } if client else {},
        "dossier_lcbft": {
            "niveau_risque": getattr(dossier, "niveau_risque", ""),
            "ppe": bool(getattr(dossier, "ppe", 0)),
        } if dossier else {},
        "motif_soupcon": decl.motif,
        "statut": "prepare_non_transmis",
        "avertissement": "Export préparé — transmission officielle ERMES/TRACFIN à effectuer "
                         "par le correspondant LCB-FT (non automatisée).",
    }
    fichier = _corbeille() / f"{ref}.json"
    fichier.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    db.commit()
    return {"reference": ref, "fichier": str(fichier), "payload": payload}


def marquer_transmise(db: Session, declaration_id: int) -> None:
    """Enregistre la confirmation, par le correspondant, d'une transmission ERMES effectuée."""
    decl = db.get(DeclarationSoupcon, declaration_id)
    if decl:
        decl.statut = "transmise"
        db.commit()
