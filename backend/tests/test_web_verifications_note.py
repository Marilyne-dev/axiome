"""Note de vérifications spécifiques : génération docx/pdf, enregistrement, cloisonnement."""
from __future__ import annotations

from _helpers_ecrans import ck

from app.models.balance import LigneBalance
from app.models.cabinet import Cabinet
from app.models.client import Client
from app.models.edition import RapportEdition
from app.models.mission import Mission


def _mission_prep(client, db, intitule="Vérif note"):
    cab = db.query(Cabinet).first()
    cl = Client(cabinet_id=cab.id, raison_sociale="Alpha SAS"); db.add(cl); db.commit()
    client.post("/vue/missions/creer", cookies=ck(client), follow_redirects=False, data={
        "client_id": cl.id, "intitule": intitule, "type_mission": "VERIF_SPEC"})
    m = db.query(Mission).filter_by(intitule=intitule).first()
    for compte, sn, mc, md in [("701000", 0, 500000, 0), ("601000", 0, 0, 420000),
                               ("101000", -100000, 0, 0), ("211000", 300000, 0, 0)]:
        db.add(LigneBalance(mission_id=m.id, compte=compte, libelle=compte,
                            solde_n=sn, mvt_credit_n=mc, mvt_debit_n=md))
    db.commit()
    client.get(f"/missions/{m.id}/vue/verifications", cookies=ck(client))
    client.post(f"/missions/{m.id}/vue/verifications/ligne/CA", cookies=ck(client),
                follow_redirects=False, data={"montant_rapport": "500000"})
    return m


def test_note_docx(client, db_session):
    m = _mission_prep(client, db_session)
    r = client.get(f"/missions/{m.id}/vue/verifications/note?format=docx", cookies=ck(client))
    assert r.status_code == 200
    assert r.content[:2] == b"PK" and len(r.content) > 5000
    assert "wordprocessingml" in r.headers.get("content-type", "")


def test_note_pdf(client, db_session):
    m = _mission_prep(client, db_session, "Vérif note pdf")
    r = client.get(f"/missions/{m.id}/vue/verifications/note?format=pdf", cookies=ck(client))
    assert r.status_code == 200
    assert r.content[:4] == b"%PDF" and len(r.content) > 3000


def test_note_enregistre_edition(client, db_session):
    m = _mission_prep(client, db_session, "Vérif note edit")
    client.get(f"/missions/{m.id}/vue/verifications/note?format=docx", cookies=ck(client))
    n = db_session.query(RapportEdition).filter_by(
        mission_id=m.id, type_edition="note-verifications").count()
    assert n == 1


def test_note_cloisonnement(client, db_session):
    autre = Cabinet(nom="Autre"); db_session.add(autre); db_session.flush()
    cl = Client(cabinet_id=autre.id, raison_sociale="Hors"); db_session.add(cl); db_session.flush()
    m = Mission(client_id=cl.id, intitule="Hors", type_mission="VERIF_SPEC",
                referentiel="PCG_FR", devise="EUR", pays="France")
    db_session.add(m); db_session.commit()
    assert client.get(f"/missions/{m.id}/vue/verifications/note?format=docx",
                      cookies=ck(client)).status_code == 403
