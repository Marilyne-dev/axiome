"""Phase 8 — écrans web additionnels : Clients et Cartographie des risques."""
from __future__ import annotations

from app.models.audit import RiskItem
from app.models.cabinet import Cabinet
from app.models.client import Client
from app.models.mission import Mission


def _cookies(client):
    return client.post("/login", data={"email": "admin@axiome.io", "password": "Test!2026"},
                       follow_redirects=False).cookies


def _mission(db):
    cab = Cabinet(nom="Cab"); db.add(cab); db.flush()
    cl = Client(cabinet_id=cab.id, raison_sociale="Alpha SAS"); db.add(cl); db.flush()
    m = Mission(client_id=cl.id, intitule="Audit Alpha", referentiel="PCG_FR",
                pays="France", devise="EUR"); db.add(m); db.commit()
    return m.id


def test_clients_page_et_creation(client, db_session):
    ck = _cookies(client)
    assert client.get("/vue/clients", cookies=ck).status_code == 200
    r = client.post("/vue/clients", cookies=ck,
                    data={"raison_sociale": "Beta Industries", "pays": "France", "secteur": "BTP"},
                    follow_redirects=False)
    assert r.status_code == 302
    page = client.get("/vue/clients", cookies=ck)
    assert "Beta Industries" in page.text
    assert db_session.query(Client).filter_by(raison_sociale="Beta Industries").first() is not None


def test_risques_page_heatmap_et_niveau(client, db_session):
    mid = _mission(db_session)
    ck = _cookies(client)
    client.post(f"/missions/{mid}/vue/risques", cookies=ck,
                data={"libelle": "Fraude achats", "categorie": "fraude", "probabilite": 5, "impact": 5},
                follow_redirects=False)
    r = client.get(f"/missions/{mid}/vue/risques", cookies=ck)
    assert r.status_code == 200
    assert "Fraude achats" in r.text and "niv-critique" in r.text
    assert db_session.query(RiskItem).filter_by(mission_id=mid).count() == 1


def test_risque_page_mission_inexistante_404(client, db_session):
    ck = _cookies(client)
    assert client.get("/missions/99999/vue/risques", cookies=ck).status_code == 404
