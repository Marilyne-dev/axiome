"""Invitations et réinitialisation de mot de passe : cycle complet et sécurité."""
from __future__ import annotations

from _helpers_ecrans import ck

from app.models.auth_token import OutboxEmail
from app.models.user import User


def _lien(db, email):
    msg = (db.query(OutboxEmail).filter_by(destinataire=email)
           .order_by(OutboxEmail.id.desc()).first())
    return msg.lien if msg else ""


def test_invitation_cree_compte_inactif_et_email(client, db_session):
    client.post("/vue/administration/inviter", cookies=ck(client), follow_redirects=False,
                data={"email": "invite@cab.fr", "nom_complet": "Invité", "role": "COLLABORATEUR"})
    u = db_session.query(User).filter_by(email="invite@cab.fr").first()
    assert u is not None and u.is_active is False
    assert db_session.query(OutboxEmail).filter_by(destinataire="invite@cab.fr").count() == 1
    assert "/activer?token=" in _lien(db_session, "invite@cab.fr")


def test_activation_puis_login(client, db_session):
    client.post("/vue/administration/inviter", cookies=ck(client), follow_redirects=False,
                data={"email": "act@cab.fr", "role": "AUDITEUR"})
    token = _lien(db_session, "act@cab.fr").split("token=")[1]
    assert client.get(f"/activer?token={token}").status_code == 200
    client.post("/activer", follow_redirects=False,
                data={"token": token, "nom_complet": "Act", "password": "MotDePasse1"})
    db_session.expire_all()
    u = db_session.query(User).filter_by(email="act@cab.fr").first()
    assert u.is_active is True
    r = client.post("/login", follow_redirects=False,
                    data={"email": "act@cab.fr", "password": "MotDePasse1"})
    assert r.status_code in (302, 303)


def test_token_usage_unique(client, db_session):
    client.post("/vue/administration/inviter", cookies=ck(client), follow_redirects=False,
                data={"email": "once@cab.fr", "role": "COLLABORATEUR"})
    token = _lien(db_session, "once@cab.fr").split("token=")[1]
    client.post("/activer", follow_redirects=False,
                data={"token": token, "password": "MotDePasse1"})
    # réutilisation : lien invalide
    page = client.get(f"/activer?token={token}")
    assert "invalide ou expiré" in page.text


def test_reset_flow(client, db_session):
    # créer un compte actif via invitation + activation
    client.post("/vue/administration/inviter", cookies=ck(client), follow_redirects=False,
                data={"email": "reset@cab.fr", "role": "COLLABORATEUR"})
    tk = _lien(db_session, "reset@cab.fr").split("token=")[1]
    client.post("/activer", follow_redirects=False, data={"token": tk, "password": "AncienPass1"})
    # demande de réinitialisation
    client.post("/mot-de-passe-oublie", follow_redirects=False, data={"email": "reset@cab.fr"})
    rtk = _lien(db_session, "reset@cab.fr").split("token=")[1]
    client.post("/reinitialiser", follow_redirects=False,
                data={"token": rtk, "password": "NouveauPass9"})
    r = client.post("/login", follow_redirects=False,
                    data={"email": "reset@cab.fr", "password": "NouveauPass9"})
    assert r.status_code in (302, 303)


def test_reset_sans_enumeration(client, db_session):
    r = client.post("/mot-de-passe-oublie", follow_redirects=False, data={"email": "nexistepas@x.fr"})
    assert r.status_code == 302 and "envoye=1" in r.headers["location"]
    assert db_session.query(OutboxEmail).filter_by(destinataire="nexistepas@x.fr").count() == 0


def test_activer_token_invalide(client):
    page = client.get("/activer?token=nimportequoi")
    assert page.status_code == 200 and "invalide ou expiré" in page.text
