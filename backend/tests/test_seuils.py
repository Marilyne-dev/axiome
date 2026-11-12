"""Module 27 — seuils : base la plus faible retenue, ratios."""
from __future__ import annotations

from app.services.seuils_service import calculer


def test_retient_la_base_la_plus_faible():
    # RN=100k*5%=5000 ; CA=2M*1%=20000 ; CP=500k*1%=5000 -> min=5000 (RN ou CP)
    r = calculer({"resultat_net": 100_000, "chiffre_affaires": 2_000_000, "capitaux_propres": 500_000})
    assert r.seuil_signification == 5000.0
    assert r.base_retenue in {"resultat_net", "capitaux_propres"}
    assert r.seuil_planification == 3750.0     # 75 %
    assert r.seuil_remontee == 250.0           # 5 %


def test_bases_vides():
    r = calculer({"resultat_net": 0, "chiffre_affaires": 0, "capitaux_propres": 0})
    assert r.seuil_signification == 0.0


def test_endpoint_seuils(client, db_session):
    from app.models.cabinet import Cabinet
    from app.models.client import Client
    from app.models.mission import Mission
    cab = Cabinet(nom="C", pays="France"); db_session.add(cab); db_session.flush()
    cl = Client(cabinet_id=cab.id, raison_sociale="S"); db_session.add(cl); db_session.flush()
    m = Mission(client_id=cl.id, intitule="M", referentiel="PCG_FR", pays="France", devise="EUR")
    db_session.add(m); db_session.commit()
    tok = client.post("/auth/login", json={"email": "admin@axiome.io", "password": "Test!2026"}).json()["access_token"]
    h = {"Authorization": f"Bearer {tok}"}
    r = client.post(f"/missions/{m.id}/seuils", headers=h,
                    json={"resultat_net": 100_000, "chiffre_affaires": 2_000_000, "capitaux_propres": 500_000})
    assert r.status_code == 200 and r.json()["seuil_signification"] == 5000.0
