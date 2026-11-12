"""Tests Module 1 — Administration : création de comptes réservée à l'admin, RBAC."""
from __future__ import annotations

from app.core.security import hash_password
from app.models.user import Role, User


def _login(client, email, password):
    return client.post("/auth/login", json={"email": email, "password": password}).json()["access_token"]


def _make_user(db, email, password, role_code):
    role = db.query(Role).filter_by(code=role_code).first()
    u = User(email=email, hashed_password=hash_password(password), nom_complet=email,
             is_active=True)
    if role:
        u.roles.append(role)
    db.add(u); db.commit()
    return u


def test_admin_cree_un_utilisateur(client, db_session):
    tok = _login(client, "admin@axiome.io", "Test!2026")
    r = client.post("/admin/users", headers={"Authorization": f"Bearer {tok}"},
                    json={"email": "nouveau@axiome.app", "password": "MotDePasse1", "nom_complet": "Nouveau",
                          "roles": ["AUDITEUR"]})
    assert r.status_code == 201
    assert r.json()["roles"] == ["AUDITEUR"]


def test_non_admin_ne_peut_pas_creer(client, db_session):
    _make_user(db_session, "collab@axiome.app", "Collab!2026", "COLLABORATEUR")
    tok = _login(client, "collab@axiome.app", "Collab!2026")
    r = client.post("/admin/users", headers={"Authorization": f"Bearer {tok}"},
                    json={"email": "x@axiome.app", "password": "MotDePasse1", "roles": []})
    assert r.status_code == 403


def test_role_inconnu_rejete(client, db_session):
    tok = _login(client, "admin@axiome.io", "Test!2026")
    r = client.post("/admin/users", headers={"Authorization": f"Bearer {tok}"},
                    json={"email": "y@axiome.app", "password": "MotDePasse1", "roles": ["ROLE_BIDON"]})
    assert r.status_code == 422
