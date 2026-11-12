"""Quotas de licence et console éditeur : journal d'activité et boîte d'envoi."""
from __future__ import annotations

from _helpers_ecrans import ck

from app.core.security import hash_password
from app.models.cabinet import Cabinet
from app.models.client import Client
from app.models.mission import Mission
from app.models.user import Role, User


def _superadmin(client, db):
    role = db.query(Role).filter_by(code="SUPERADMIN").first()
    u = User(email="ed@test.io", hashed_password=hash_password("Ed!2026"),
             nom_complet="Éditeur", is_active=True)
    u.roles.append(role)
    db.add(u); db.commit()
    return client.post("/login", data={"email": "ed@test.io", "password": "Ed!2026"},
                       follow_redirects=False).cookies


def test_quota_collaborateurs_bloque(client, db_session):
    cab = db_session.query(Cabinet).first()
    nb = db_session.query(User).filter_by(cabinet_id=cab.id, is_archived=False).count()
    cab.quota_collaborateurs = nb  # quota atteint
    db_session.commit()
    r = client.post("/vue/administration/collaborateur", cookies=ck(client), follow_redirects=False,
                    data={"email": "trop@cab.fr", "role": "COLLABORATEUR", "password": "password12"})
    assert r.headers.get("location", "").endswith("err=quota")


def test_quota_missions_bloque(client, db_session):
    cab = db_session.query(Cabinet).first()
    cl = Client(cabinet_id=cab.id, raison_sociale="QuotaCo"); db_session.add(cl); db_session.commit()
    nb = (db_session.query(Mission).join(Client, Mission.client_id == Client.id)
          .filter(Client.cabinet_id == cab.id).count())
    cab.quota_missions = nb + 1
    db_session.commit()
    r1 = client.post("/vue/missions/creer", cookies=ck(client), follow_redirects=False,
                     data={"client_id": cl.id, "intitule": "M1", "type_mission": "CERT_ANNUELS"})
    assert r1.status_code == 302 and "err=" not in r1.headers["location"]
    r2 = client.post("/vue/missions/creer", cookies=ck(client), follow_redirects=False,
                     data={"client_id": cl.id, "intitule": "M2", "type_mission": "CERT_ANNUELS"})
    assert r2.headers.get("location", "").endswith("err=quota_missions")


def test_console_definit_quotas(client, db_session):
    ck_sa = _superadmin(client, db_session)
    cab = db_session.query(Cabinet).first()
    client.post(f"/console/cabinet/{cab.id}/quotas", cookies=ck_sa, follow_redirects=False,
                data={"quota_collaborateurs": "5", "quota_missions": "20"})
    db_session.expire_all()
    cab = db_session.get(Cabinet, cab.id)
    assert cab.quota_collaborateurs == 5 and cab.quota_missions == 20


def test_console_journal_et_outbox(client, db_session):
    ck_sa = _superadmin(client, db_session)
    cab = db_session.query(Cabinet).first()
    assert client.get(f"/console/cabinet/{cab.id}/journal", cookies=ck_sa).status_code == 200
    assert client.get("/console/outbox", cookies=ck_sa).status_code == 200


def test_journal_refuse_admin_cabinet(client, db_session):
    cab = db_session.query(Cabinet).first()
    assert client.get(f"/console/cabinet/{cab.id}/journal", cookies=ck(client)).status_code == 403
