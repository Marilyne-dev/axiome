"""Phase 8 — écran LCB‑FT : confidentialité (admin refusé) + workflow correspondant."""
from __future__ import annotations

from app.core.security import hash_password
from app.models.audit import AuditLog
from app.models.cabinet import Cabinet
from app.models.client import Client
from app.models.lcbft import DossierLCBFT
from app.models.user import Role, User


def _correspondant(db):
    role = db.query(Role).filter_by(code="CORRESPONDANT_LCBFT").first()
    u = User(email="corr@axiome.io", hashed_password=hash_password("Corr!2026"),
             nom_complet="Corr", is_active=True)
    u.roles.append(role); db.add(u); db.commit()


def _client(db):
    cab = Cabinet(nom="C"); db.add(cab); db.flush()
    c = Client(cabinet_id=cab.id, raison_sociale="Suspecte SARL"); db.add(c); db.commit()
    return c.id


def _ck(client, email, pwd):
    return client.post("/login", data={"email": email, "password": pwd}, follow_redirects=False).cookies


def test_admin_refuse_ecran_lcbft(client, db_session):
    _correspondant(db_session); _client(db_session)
    r = client.get("/vue/lcbft", cookies=_ck(client, "admin@axiome.io", "Test!2026"))
    assert r.status_code == 403 and "Accès restreint" in r.text


def test_correspondant_workflow(client, db_session):
    _correspondant(db_session); cid = _client(db_session)
    ck = _ck(client, "corr@axiome.io", "Corr!2026")
    assert client.get("/vue/lcbft", cookies=ck).status_code == 200
    # ouvrir dossier
    client.post("/vue/lcbft", cookies=ck, data={"client_id": cid}, follow_redirects=False)
    d = db_session.query(DossierLCBFT).filter_by(client_id=cid).first()
    assert d is not None
    # classifier PPE -> risque élevé
    client.post(f"/vue/lcbft/{d.id}/classification", cookies=ck, data={"ppe": "on"}, follow_redirects=False)
    db_session.expire_all()
    assert db_session.get(DossierLCBFT, d.id).niveau_risque == "eleve"
    # screening (redirection avec résultat)
    r = client.post(f"/vue/lcbft/{d.id}/screening", cookies=ck,
                    data={"nom": "John Doe Sanctionné"}, follow_redirects=False)
    assert "renforcee" in r.headers["location"]
    # déclaration
    client.post(f"/vue/lcbft/{d.id}/declaration", cookies=ck,
                data={"motif": "Flux atypiques"}, follow_redirects=False)
    db_session.expire_all()
    assert len(db_session.get(DossierLCBFT, d.id).declarations) == 1
    # accès journalisés
    assert db_session.query(AuditLog).filter(AuditLog.action.like("lcbft.web.%")).count() >= 4
