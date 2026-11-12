"""Modules 14/16 — assistant IA : dégradation gracieuse sans clé API."""
from __future__ import annotations


def _token(client):
    return client.post("/auth/login", json={"email": "admin@axiome.io", "password": "Test!2026"}).json()["access_token"]


def test_statut_ia_sans_cle(client):
    h = {"Authorization": f"Bearer {_token(client)}"}
    assert client.get("/ia/statut", headers=h).json()["disponible"] is False


def test_assister_sans_cle(client):
    h = {"Authorization": f"Bearer {_token(client)}"}
    r = client.post("/ia/assister", headers=h, json={"prompt": "Rédige une note de synthèse."}).json()
    assert r["disponible"] is False and "non configuré" in r["message"]
