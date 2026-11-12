"""Module CSRD : double matérialité, génération/suppression des points, couverture, cloisonnement."""
from __future__ import annotations

from _helpers_ecrans import ck

from app.core import esrs_ref
from app.models.cabinet import Cabinet
from app.models.client import Client
from app.models.csrd import CsrdMateriality, CsrdPoint
from app.models.mission import Mission


def _mission_csrd(client, db, intitule="CSRD"):
    cab = db.query(Cabinet).first()
    cl = Client(cabinet_id=cab.id, raison_sociale="Verde SAS"); db.add(cl); db.commit()
    client.post("/vue/missions/creer", cookies=ck(client), follow_redirects=False, data={
        "client_id": cl.id, "intitule": intitule, "type_mission": "CSRD_ESG"})
    return db.query(Mission).filter_by(intitule=intitule).first()


def test_csrd_page_et_dix_themes(client, db_session):
    m = _mission_csrd(client, db_session)
    page = client.get(f"/missions/{m.id}/vue/csrd", cookies=ck(client))
    assert page.status_code == 200
    for code in ["E1", "E5", "S1", "S4", "G1"]:
        assert code in page.text
    # ensure a créé les 10 lignes de matérialité
    assert db_session.query(CsrdMateriality).filter_by(mission_id=m.id).count() == len(esrs_ref.THEMES)


def test_materialite_retenue_genere_les_points(client, db_session):
    m = _mission_csrd(client, db_session)
    client.get(f"/missions/{m.id}/vue/csrd", cookies=ck(client))  # init
    client.post(f"/missions/{m.id}/vue/csrd/materialite/E1", cookies=ck(client),
                follow_redirects=False, data={"impact": "3", "financier": "1", "justification": "x"})
    e1 = db_session.query(CsrdMateriality).filter_by(mission_id=m.id, esrs_code="E1").first()
    assert e1.retenu is True
    pts = db_session.query(CsrdPoint).filter_by(mission_id=m.id, esrs_code="E1").all()
    assert len(pts) == len(esrs_ref.points_du_theme("E1")) and len(pts) > 0


def test_theme_non_materiel_sans_points(client, db_session):
    m = _mission_csrd(client, db_session)
    client.get(f"/missions/{m.id}/vue/csrd", cookies=ck(client))
    client.post(f"/missions/{m.id}/vue/csrd/materialite/S2", cookies=ck(client),
                follow_redirects=False, data={"impact": "1", "financier": "0"})
    s2 = db_session.query(CsrdMateriality).filter_by(mission_id=m.id, esrs_code="S2").first()
    assert s2.retenu is False
    assert db_session.query(CsrdPoint).filter_by(mission_id=m.id, esrs_code="S2").count() == 0


def test_points_supprimes_si_theme_redevient_non_materiel(client, db_session):
    m = _mission_csrd(client, db_session)
    client.get(f"/missions/{m.id}/vue/csrd", cookies=ck(client))
    client.post(f"/missions/{m.id}/vue/csrd/materialite/E1", cookies=ck(client),
                follow_redirects=False, data={"impact": "3", "financier": "0"})
    assert db_session.query(CsrdPoint).filter_by(mission_id=m.id, esrs_code="E1").count() > 0
    client.post(f"/missions/{m.id}/vue/csrd/materialite/E1", cookies=ck(client),
                follow_redirects=False, data={"impact": "0", "financier": "0"})
    assert db_session.query(CsrdPoint).filter_by(mission_id=m.id, esrs_code="E1").count() == 0


def test_toggle_point_couverture(client, db_session):
    m = _mission_csrd(client, db_session)
    client.get(f"/missions/{m.id}/vue/csrd", cookies=ck(client))
    client.post(f"/missions/{m.id}/vue/csrd/materialite/G1", cookies=ck(client),
                follow_redirects=False, data={"impact": "2", "financier": "2"})
    p = db_session.query(CsrdPoint).filter_by(mission_id=m.id, esrs_code="G1").first()
    assert p.couvert is False
    client.post(f"/missions/{m.id}/vue/csrd/point/{p.id}/toggle", cookies=ck(client),
                follow_redirects=False)
    db_session.refresh(p)
    assert p.couvert is True


def test_csrd_cloisonnement(client, db_session):
    autre = Cabinet(nom="Autre"); db_session.add(autre); db_session.flush()
    cl = Client(cabinet_id=autre.id, raison_sociale="Hors"); db_session.add(cl); db_session.flush()
    m = Mission(client_id=cl.id, intitule="Hors périmètre", type_mission="CSRD_ESG",
                referentiel="PCG_FR", devise="EUR", pays="France")
    db_session.add(m); db_session.commit()
    assert client.get(f"/missions/{m.id}/vue/csrd", cookies=ck(client)).status_code == 403
