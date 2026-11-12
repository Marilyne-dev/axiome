"""Module 13 bis — LCB-FT : confidentialité (accès restreint) + journalisation."""
from __future__ import annotations

from app.core.security import hash_password
from app.models.audit import AuditLog
from app.models.cabinet import Cabinet
from app.models.client import Client
from app.models.user import Role, User


def _correspondant(db):
    role = db.query(Role).filter_by(code="CORRESPONDANT_LCBFT").first()
    u = User(email="lcbft@axiome.io", hashed_password=hash_password("Lcbft!2026"),
             nom_complet="Corr LCBFT", is_active=True)
    u.roles.append(role); db.add(u); db.commit()
    return u


def _client(db):
    cab = Cabinet(nom="C"); db.add(cab); db.flush()
    c = Client(cabinet_id=cab.id, raison_sociale="Suspecte SARL"); db.add(c); db.commit()
    return c.id


def _token(client, email, pwd):
    return client.post("/auth/login", json={"email": email, "password": pwd}).json()["access_token"]


def test_admin_refuse_sur_lcbft(client, db_session):
    """L'ADMIN lui-même n'accède pas au LCB-FT (confidentialité stricte)."""
    _correspondant(db_session); cid = _client(db_session)
    tok = _token(client, "admin@axiome.io", "Test!2026")
    r = client.post("/lcbft/dossiers", headers={"Authorization": f"Bearer {tok}"}, json={"client_id": cid})
    assert r.status_code == 403


def test_correspondant_accede_et_est_journalise(client, db_session):
    _correspondant(db_session); cid = _client(db_session)
    h = {"Authorization": f"Bearer {_token(client, 'lcbft@axiome.io', 'Lcbft!2026')}"}
    r = client.post("/lcbft/dossiers", headers=h, json={"client_id": cid})
    assert r.status_code == 201
    did = r.json()["id"]
    # classification élevée si PPE
    cl = client.post(f"/lcbft/dossiers/{did}/classification", headers=h, json={"ppe": True}).json()
    assert cl["niveau_risque"] == "eleve"
    # déclaration de soupçon confidentielle
    decl = client.post(f"/lcbft/dossiers/{did}/declarations", headers=h, json={"motif": "Flux atypiques"})
    assert decl.status_code == 201
    # chaque accès est journalisé
    logs = db_session.query(AuditLog).filter(AuditLog.action.like("lcbft.%")).all()
    assert len(logs) >= 3


def test_screening_detecte_sanction(client, db_session):
    _correspondant(db_session)
    h = {"Authorization": f"Bearer {_token(client, 'lcbft@axiome.io', 'Lcbft!2026')}"}
    r = client.post("/lcbft/screening", headers=h, json={"nom": "John Doe Sanctionné"}).json()
    assert r["match_sanctions"] is True and r["vigilance"] == "renforcee"
