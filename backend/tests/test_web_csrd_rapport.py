"""Rapport d'assurance CSRD : génération docx/pdf, enregistrement de l'édition, cloisonnement."""
from __future__ import annotations

from _helpers_ecrans import ck

from app.models.cabinet import Cabinet
from app.models.client import Client
from app.models.edition import RapportEdition
from app.models.mission import Mission


def _mission_csrd_prep(client, db, intitule="CSRD rapport"):
    cab = db.query(Cabinet).first()
    cl = Client(cabinet_id=cab.id, raison_sociale="Verde SAS"); db.add(cl); db.commit()
    client.post("/vue/missions/creer", cookies=ck(client), follow_redirects=False, data={
        "client_id": cl.id, "intitule": intitule, "type_mission": "CSRD_ESG"})
    m = db.query(Mission).filter_by(intitule=intitule).first()
    client.get(f"/missions/{m.id}/vue/csrd", cookies=ck(client))
    client.post(f"/missions/{m.id}/vue/csrd/materialite/E1", cookies=ck(client),
                follow_redirects=False, data={"impact": "3", "financier": "2"})
    return m


def test_rapport_docx(client, db_session):
    m = _mission_csrd_prep(client, db_session)
    r = client.get(f"/missions/{m.id}/vue/csrd/rapport?format=docx", cookies=ck(client))
    assert r.status_code == 200
    assert r.content[:2] == b"PK" and len(r.content) > 5000
    assert "wordprocessingml" in r.headers.get("content-type", "")


def test_rapport_pdf(client, db_session):
    m = _mission_csrd_prep(client, db_session, "CSRD pdf")
    r = client.get(f"/missions/{m.id}/vue/csrd/rapport?format=pdf", cookies=ck(client))
    assert r.status_code == 200
    assert r.content[:4] == b"%PDF" and len(r.content) > 3000
    assert r.headers.get("content-type", "").startswith("application/pdf")


def test_rapport_enregistre_edition(client, db_session):
    m = _mission_csrd_prep(client, db_session, "CSRD edition")
    client.get(f"/missions/{m.id}/vue/csrd/rapport?format=docx", cookies=ck(client))
    n = db_session.query(RapportEdition).filter_by(
        mission_id=m.id, type_edition="rapport-csrd").count()
    assert n == 1


def test_rapport_cloisonnement(client, db_session):
    autre = Cabinet(nom="Autre"); db_session.add(autre); db_session.flush()
    cl = Client(cabinet_id=autre.id, raison_sociale="Hors"); db_session.add(cl); db_session.flush()
    m = Mission(client_id=cl.id, intitule="Hors périmètre", type_mission="CSRD_ESG",
                referentiel="PCG_FR", devise="EUR", pays="France")
    db_session.add(m); db_session.commit()
    assert client.get(f"/missions/{m.id}/vue/csrd/rapport?format=docx",
                      cookies=ck(client)).status_code == 403
