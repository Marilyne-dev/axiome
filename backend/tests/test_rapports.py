"""Module 17 — génération des rapports Word/PDF."""
from __future__ import annotations

import io

from docx import Document

from app.models.cabinet import Cabinet
from app.models.client import Client
from app.models.mission import Mission


def _mission(db):
    cab = Cabinet(nom="Cab"); db.add(cab); db.flush()
    cl = Client(cabinet_id=cab.id, raison_sociale="Alpha SAS"); db.add(cl); db.flush()
    m = Mission(client_id=cl.id, intitule="Audit Alpha 2025", referentiel="PCG_FR",
                pays="France", devise="EUR"); db.add(m); db.commit()
    return m.id


def _tok(client):
    return client.post("/auth/login", json={"email": "admin@axiome.io", "password": "Test!2026"}).json()["access_token"]


def _texte_docx(contenu: bytes) -> str:
    doc = Document(io.BytesIO(contenu))
    parts = [p.text for p in doc.paragraphs]
    for tbl in doc.tables:
        for row in tbl.rows:
            parts += [c.text for c in row.cells]
    return "\n".join(parts)


def test_lettre_mission_docx(client, db_session):
    mid = _mission(db_session)
    h = {"Authorization": f"Bearer {_tok(client)}"}
    r = client.get(f"/missions/{mid}/rapports/lettre-mission?format=docx", headers=h)
    assert r.status_code == 200 and r.content[:2] == b"PK"
    txt = _texte_docx(r.content)
    assert "Lettre de mission" in txt and "NEP 210" in txt and "Alpha SAS" in txt


def test_rapport_general_docx(client, db_session):
    mid = _mission(db_session)
    h = {"Authorization": f"Bearer {_tok(client)}"}
    r = client.get(f"/missions/{mid}/rapports/rapport-general?format=docx", headers=h)
    txt = _texte_docx(r.content)
    assert "Opinion" in txt and "Fondement de l'opinion" in txt


def test_type_inconnu_404(client, db_session):
    mid = _mission(db_session)
    h = {"Authorization": f"Bearer {_tok(client)}"}
    assert client.get(f"/missions/{mid}/rapports/inexistant", headers=h).status_code == 404


def test_note_synthese_pdf(client, db_session):
    mid = _mission(db_session)
    h = {"Authorization": f"Bearer {_tok(client)}"}
    r = client.get(f"/missions/{mid}/rapports/note-synthese?format=pdf", headers=h)
    assert r.status_code == 200 and r.content[:5] == b"%PDF-"
