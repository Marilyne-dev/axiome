"""Module 7 — risques : ajout, priorisation, heat map."""
from __future__ import annotations

from tests._helpers import admin_headers, mission_cycle


def test_heatmap_et_priorisation(client, db_session):
    h = admin_headers(client); mid, _ = mission_cycle(db_session)
    client.post(f"/missions/{mid}/risques", headers=h, json={"libelle": "Faible", "probabilite": 1, "impact": 1})
    client.post(f"/missions/{mid}/risques", headers=h, json={"libelle": "Critique", "categorie": "fraude", "probabilite": 5, "impact": 5})
    lst = client.get(f"/missions/{mid}/risques", headers=h).json()
    assert lst[0]["libelle"] == "Critique"  # priorisé en tête (score 25)
    hm = client.get(f"/missions/{mid}/risques/heatmap", headers=h).json()
    assert hm["par_niveau"]["critique"] == 1 and hm["total"] == 2


def test_bornes_probabilite(client, db_session):
    h = admin_headers(client); mid, _ = mission_cycle(db_session)
    r = client.post(f"/missions/{mid}/risques", headers=h, json={"libelle": "X", "probabilite": 9, "impact": 1})
    assert r.status_code == 422  # proba hors 1..5
