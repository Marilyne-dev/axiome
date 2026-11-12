"""Phase 8 — pages web (rendu serveur) : liste des missions et espace de travail."""
from __future__ import annotations

from app.models.cabinet import Cabinet
from app.models.client import Client
from app.models.mission import Mission


def _mission(db):
    cab = db.query(Cabinet).first()
    if cab is None:
        cab = Cabinet(nom="Cab"); db.add(cab); db.flush()
    cl = Client(cabinet_id=cab.id, raison_sociale="Alpha SAS"); db.add(cl); db.flush()
    m = Mission(client_id=cl.id, intitule="Audit Alpha 2025", referentiel="PCG_FR",
                pays="France", devise="EUR"); db.add(m); db.commit()
    return m.id


def _login(client):
    return client.post("/login", data={"email": "admin@axiome.io", "password": "Test!2026"},
                       follow_redirects=False).cookies


def test_page_missions(client, db_session):
    _mission(db_session)
    ck = _login(client)
    r = client.get("/missions", cookies=ck)
    assert r.status_code == 200
    assert "Audit Alpha 2025" in r.text and "Ouvrir le dossier" in r.text


def test_espace_travail_mission(client, db_session):
    mid = _mission(db_session)
    ck = _login(client)
    r = client.get(f"/missions/{mid}/vue", cookies=ck)
    assert r.status_code == 200
    assert r.text.count('name="conclusion"') == 13     # 13 cycles éditables
    assert "import-web" in r.text                    # formulaire d'import présent


def test_acces_web_sans_auth_redirige(client):
    r = client.get("/missions", follow_redirects=False)
    assert r.status_code == 302 and r.headers["location"] == "/login"
