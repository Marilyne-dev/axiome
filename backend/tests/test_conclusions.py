"""Conclusions par cycle éditables + alimentation de la note de synthèse."""
from __future__ import annotations

import io

from docx import Document

from app.models.cabinet import Cabinet
from app.models.client import Client
from app.models.conclusion import CycleConclusion
from app.models.mission import Mission


def _mission(db):
    cab = Cabinet(nom="Cab"); db.add(cab); db.flush()
    cl = Client(cabinet_id=cab.id, raison_sociale="Alpha SAS"); db.add(cl); db.flush()
    m = Mission(client_id=cl.id, intitule="Audit Alpha 2025", referentiel="PCG_FR",
                pays="France", devise="EUR"); db.add(m); db.commit()
    return m.id


def _cookies(client):
    return client.post("/login", data={"email": "admin@axiome.io", "password": "Test!2026"},
                       follow_redirects=False).cookies


def test_conclusion_persistee_et_dans_note(client, db_session):
    mid = _mission(db_session)
    ck = _cookies(client)
    r = client.post(f"/missions/{mid}/cycles/EMPRUNTS/conclusion-web", cookies=ck,
                    data={"conclusion": "Emprunts circularisés, RAS.", "anomalie": "on"},
                    follow_redirects=False)
    assert r.status_code == 302
    obj = db_session.query(CycleConclusion).filter_by(mission_id=mid, cycle_code="EMPRUNTS").first()
    assert obj and obj.anomalie is True and "circularisés" in obj.conclusion
    # la note de synthèse reprend la conclusion
    h = {"Authorization": f"Bearer {client.post('/auth/login', json={'email':'admin@axiome.io','password':'Test!2026'}).json()['access_token']}"}
    note = client.get(f"/missions/{mid}/rapports/note-synthese?format=docx", headers=h).content
    doc = Document(io.BytesIO(note))
    txt = "\n".join(c.text for t in doc.tables for row in t.rows for c in row.cells)
    assert "Emprunts circularisés, RAS." in txt
