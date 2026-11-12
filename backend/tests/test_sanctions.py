"""Phase 5 — screening de sanctions : repli démo + fournisseur par fichier."""
from __future__ import annotations

from pathlib import Path

from app.core.config import settings
from app.services import lcbft_service, sanctions_service


def test_repli_demo():
    r = sanctions_service.screener("John Doe Sanctionne")
    assert r["match"] is True and r["source"] == "demo"
    assert sanctions_service.screener("Client Lambda")["match"] is False


def test_fournisseur_fichier(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))
    liste = Path(tmp_path) / "sanctions" / "liste.csv"
    liste.parent.mkdir(parents=True)
    liste.write_text("nom,type,programme,source\nEntite Suspecte SARL,entite,UE,ue\n")
    assert sanctions_service.source_active()["origine"] == "fichier"
    r = sanctions_service.screener("La Entite Suspecte SARL de Paris")
    assert r["match"] is True and r["source"] == "fichier"
    # le screening LCB-FT consomme bien le fichier
    assert lcbft_service.screening("Entite Suspecte SARL")["match_sanctions"] is True
