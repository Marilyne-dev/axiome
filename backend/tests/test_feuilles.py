"""Module 10 — feuilles de travail : création + validation."""
from __future__ import annotations

from tests._helpers import admin_headers, mission_cycle


def test_feuille_creation_validation(client, db_session):
    h = admin_headers(client); _, cid = mission_cycle(db_session)
    fid = client.post(f"/cycles/{cid}/feuilles", headers=h,
                      json={"reference": "FMA", "titre": "Feuille maîtresse Trésorerie"}).json()["id"]
    r = client.patch(f"/cycles/{cid}/feuilles/{fid}/valider", headers=h)
    assert r.status_code == 200 and r.json()["statut"] == "validee"
