"""Phase 8 — écran de détection de fraude (Benford + indicateurs)."""
from __future__ import annotations

from app.models.balance import LigneBalance
from app.models.cabinet import Cabinet
from app.models.client import Client
from app.models.mission import Mission
from app.services.benford_service import BENFORD


def _ck(client):
    return client.post("/login", data={"email": "admin@axiome.io", "password": "Test!2026"},
                       follow_redirects=False).cookies


def _mission_benford(db):
    cab = Cabinet(nom="Cab"); db.add(cab); db.flush()
    cl = Client(cabinet_id=cab.id, raison_sociale="Alpha"); db.add(cl); db.flush()
    m = Mission(client_id=cl.id, intitule="Audit", referentiel="PCG_FR",
                pays="France", devise="EUR"); db.add(m); db.flush()
    for d in range(1, 10):
        for _ in range(round(200 * BENFORD[d])):
            db.add(LigneBalance(mission_id=m.id, compte=f"{d}0", libelle="x",
                                cs_standard="", solde_n=float(f"{d}12.3")))
    db.commit()
    return m.id


def test_page_fraude_conforme(client, db_session):
    mid = _mission_benford(db_session)
    r = client.get(f"/missions/{mid}/vue/fraude", cookies=_ck(client))
    assert r.status_code == 200
    assert "Loi de Benford" in r.text and "conforme" in r.text
    assert "Indicateurs complémentaires" in r.text


def test_page_fraude_sans_balance(client, db_session):
    cab = Cabinet(nom="C"); db_session.add(cab); db_session.flush()
    cl = Client(cabinet_id=cab.id, raison_sociale="X"); db_session.add(cl); db_session.flush()
    m = Mission(client_id=cl.id, intitule="M", referentiel="PCG_FR", pays="France", devise="EUR")
    db_session.add(m); db_session.commit()
    r = client.get(f"/missions/{m.id}/vue/fraude", cookies=_ck(client))
    assert r.status_code == 200 and "Importez d'abord une balance" in r.text
