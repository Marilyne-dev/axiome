"""Tests Module 2 — Clients : CRUD + archivage logique + RBAC."""
from __future__ import annotations


def _admin_token(client):
    return client.post("/auth/login", json={"email": "admin@axiome.io", "password": "Test!2026"}).json()["access_token"]


def test_creation_et_liste_client(client):
    h = {"Authorization": f"Bearer {_admin_token(client)}"}
    r = client.post("/clients", headers=h, json={"raison_sociale": "Gamma SARL", "pays": "France"})
    assert r.status_code == 201
    cid = r.json()["id"]
    lst = client.get("/clients", headers=h).json()
    assert any(c["id"] == cid for c in lst)


def test_archivage_client(client):
    h = {"Authorization": f"Bearer {_admin_token(client)}"}
    cid = client.post("/clients", headers=h, json={"raison_sociale": "Delta SA"}).json()["id"]
    assert client.delete(f"/clients/{cid}", headers=h).json()["archived"] is True
    # N'apparaît plus par défaut, réapparaît si on inclut les archives.
    assert all(c["id"] != cid for c in client.get("/clients", headers=h).json())
    assert any(c["id"] == cid for c in client.get("/clients?inclure_archives=true", headers=h).json())


def test_sous_ressource_banque(client):
    h = {"Authorization": f"Bearer {_admin_token(client)}"}
    cid = client.post("/clients", headers=h, json={"raison_sociale": "Epsilon"}).json()["id"]
    r = client.post(f"/clients/{cid}/banques", headers=h, json={"banque": "BNP", "iban": "FR76...", "devise": "EUR"})
    assert r.status_code == 201 and r.json()["banque"] == "BNP"
