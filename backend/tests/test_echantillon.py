"""Module 11 — échantillonnage : tailles MUS/attributs + service."""
from __future__ import annotations

from app.services.echantillon_service import taille_attributs, taille_mus
from tests._helpers import admin_headers, mission_cycle


def test_service_taille_mus():
    # VP=1 000 000, tolérable=50 000, confiance 95% (RF=3) -> 60
    assert taille_mus(1_000_000, 50_000, 0.95) == 60


def test_service_taille_attributs():
    # taux tolérable 5%, confiance 95% (RF=3) -> 60
    assert taille_attributs(0.05, 0.95) == 60


def test_creation_echantillon_mus(client, db_session):
    h = admin_headers(client); _, cid = mission_cycle(db_session)
    r = client.post(f"/cycles/{cid}/echantillons", headers=h,
                    json={"methode": "mus", "valeur_population": 1_000_000, "seuil_tolerable": 50_000, "confiance": 0.95})
    assert r.status_code == 201 and r.json()["taille"] == 60
