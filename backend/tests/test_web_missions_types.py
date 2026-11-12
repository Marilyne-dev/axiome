"""Typologie des missions CAC : création typée, diligences, catalogue, cloisonnement."""
from __future__ import annotations

from _helpers_ecrans import ck

from app.core.missions_ref import TYPES_MISSION
from app.models.cabinet import Cabinet
from app.models.client import Client
from app.models.mission import Mission, MissionDiligence


def _client_du_cabinet(db):
    cab = db.query(Cabinet).first()
    cl = Client(cabinet_id=cab.id, raison_sociale="Gamma SAS")
    db.add(cl); db.commit()
    return cl


def test_creer_mission_avec_type(client, db_session):
    cl = _client_du_cabinet(db_session)
    r = client.post("/vue/missions/creer", cookies=ck(client), follow_redirects=False, data={
        "client_id": cl.id, "intitule": "Assurance durabilité 2025",
        "type_mission": "CSRD_ESG", "exercice": "2025",
        "referentiel": "PCG_FR", "devise": "EUR"})
    assert r.status_code == 302 and "/vue" in r.headers["location"]
    m = db_session.query(Mission).filter_by(intitule="Assurance durabilité 2025").first()
    assert m is not None and m.type_mission == "CSRD_ESG"


def test_type_inconnu_retombe_sur_defaut(client, db_session):
    cl = _client_du_cabinet(db_session)
    client.post("/vue/missions/creer", cookies=ck(client), follow_redirects=False, data={
        "client_id": cl.id, "intitule": "Mission X", "type_mission": "INEXISTANT"})
    m = db_session.query(Mission).filter_by(intitule="Mission X").first()
    assert m is not None and m.type_mission == "CERT_ANNUELS"


def test_diligences_generees_selon_type(client, db_session):
    cl = _client_du_cabinet(db_session)
    client.post("/vue/missions/creer", cookies=ck(client), follow_redirects=False, data={
        "client_id": cl.id, "intitule": "Fusion 2025", "type_mission": "FUSION_APPORT"})
    m = db_session.query(Mission).filter_by(intitule="Fusion 2025").first()
    page = client.get(f"/missions/{m.id}/vue", cookies=ck(client))
    assert page.status_code == 200
    attendu = TYPES_MISSION["FUSION_APPORT"]["diligences"]
    rows = db_session.query(MissionDiligence).filter_by(mission_id=m.id).all()
    assert len(rows) == len(attendu)
    assert {r.libelle for r in rows} == set(attendu)
    assert "parité" in page.text.lower()


def test_toggle_diligence(client, db_session):
    cl = _client_du_cabinet(db_session)
    client.post("/vue/missions/creer", cookies=ck(client), follow_redirects=False, data={
        "client_id": cl.id, "intitule": "Alerte 2025", "type_mission": "ALERTE"})
    m = db_session.query(Mission).filter_by(intitule="Alerte 2025").first()
    client.get(f"/missions/{m.id}/vue", cookies=ck(client))  # génère les diligences
    d = db_session.query(MissionDiligence).filter_by(mission_id=m.id).first()
    assert d.fait is False
    client.post(f"/missions/{m.id}/vue/diligence/{d.id}/toggle", cookies=ck(client),
                follow_redirects=False)
    db_session.refresh(d)
    assert d.fait is True


def test_catalogue_liste_les_categories(client):
    page = client.get("/vue/catalogue", cookies=ck(client))
    assert page.status_code == 200
    for cat in ["Certification", "Durabilité", "Contrôle", "Alerte", "Judiciaire",
                "Capital", "Assurance", "Contractuelle", "Organismes"]:
        assert cat in page.text


def test_creation_mission_hors_cabinet_refusee(client, db_session):
    autre = Cabinet(nom="Autre"); db_session.add(autre); db_session.flush()
    cl = Client(cabinet_id=autre.id, raison_sociale="Delta"); db_session.add(cl); db_session.commit()
    r = client.post("/vue/missions/creer", cookies=ck(client), follow_redirects=False, data={
        "client_id": cl.id, "intitule": "Pirate", "type_mission": "CERT_ANNUELS"})
    assert r.status_code == 403
    assert db_session.query(Mission).filter_by(intitule="Pirate").first() is None
