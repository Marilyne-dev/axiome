"""Phase 5 — préparation d'export TRACFIN (corbeille de sortie) + transmission."""
from __future__ import annotations

import json
from pathlib import Path

from app.core.config import settings
from app.models.cabinet import Cabinet
from app.models.client import Client
from app.models.lcbft import DeclarationSoupcon, DossierLCBFT
from app.services import tracfin_service


def _decl(db):
    cab = Cabinet(nom="Cab"); db.add(cab); db.flush()
    cl = Client(cabinet_id=cab.id, raison_sociale="Alpha", identifiant_legal="812", pays="France")
    db.add(cl); db.flush()
    dos = DossierLCBFT(client_id=cl.id, niveau_risque="eleve", ppe=1); db.add(dos); db.flush()
    d = DeclarationSoupcon(dossier_id=dos.id, motif="Flux inhabituels"); db.add(d); db.commit()
    return d.id


def test_preparer_export_et_transmise(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))
    did = _decl(db_session)
    res = tracfin_service.preparer_export(db_session, did)
    fichier = Path(res["fichier"])
    assert fichier.exists()
    data = json.loads(fichier.read_text(encoding="utf-8"))
    assert data["statut"] == "prepare_non_transmis"
    assert data["client"]["raison_sociale"] == "Alpha"
    assert data["dossier_lcbft"]["niveau_risque"] == "eleve"
    # confirmation de transmission (acte du correspondant)
    tracfin_service.marquer_transmise(db_session, did)
    db_session.expire_all()
    assert db_session.get(DeclarationSoupcon, did).statut == "transmise"
