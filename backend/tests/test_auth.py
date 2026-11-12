"""Tests d'authentification : succès, échec, protection des routes."""
from __future__ import annotations


def test_login_ok(client):
    r = client.post("/auth/login", json={"email": "admin@axiome.io", "password": "Test!2026"})
    assert r.status_code == 200
    data = r.json()
    assert data["access_token"] and data["token_type"] == "bearer"


def test_login_mauvais_mdp(client):
    r = client.post("/auth/login", json={"email": "admin@axiome.io", "password": "faux"})
    assert r.status_code == 401


def test_route_protegee_sans_jeton(client):
    assert client.get("/auth/me").status_code == 401


def test_route_protegee_avec_jeton(client):
    tok = client.post("/auth/login", json={"email": "admin@axiome.io", "password": "Test!2026"}).json()["access_token"]
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200 and r.json()["email"] == "admin@axiome.io"
