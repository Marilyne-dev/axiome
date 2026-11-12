"""Espace cabinet : création client/mission, détail, et CLOISONNEMENT des routes JSON par cabinet."""
from __future__ import annotations

import pytest

from app.services import billing_service

pytestmark = pytest.mark.cloisonnement

SIGNUP = {"plan_code": "cabinet", "periode": "mensuel", "devise": "EUR", "cabinet_nom": "Cabinet A", "pays": "France",
          "admin_nom": "Alice A", "admin_email": "alice@a.fr", "admin_password": "MotDePasse2026"}


@pytest.fixture()
def deux_cabinets(client, db_session):
    billing_service.seed_plans(db_session); db_session.commit()
    heads = []
    for nom, email in (("Cabinet A", "alice@a.fr"), ("Cabinet B", "bob@b.fr")):
        ref = client.post("/public/signup", json={**SIGNUP, "cabinet_nom": nom, "admin_email": email}).json()["reference"]
        assert client.post(f"/public/paiements/{ref}/confirmer-test").json()["statut"] == "paye"
        tok = client.post("/auth/login", json={"email": email, "password": "MotDePasse2026"}).json()["access_token"]
        heads.append({"Authorization": f"Bearer {tok}"})
    return heads


def _mission(client, h, intitule="Certification 2026"):
    cid = client.post("/espace/clients", json={"raison_sociale": "Société Test SA"}, headers=h).json()["id"]
    r = client.post("/espace/missions", json={"client_id": cid, "intitule": intitule, "exercice": "2026"}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_creation_et_detail_mission(client, deux_cabinets):
    a, _ = deux_cabinets
    opts = client.get("/espace/referentiels-types", headers=a).json()
    assert opts["referentiels"] and any(t["code"] == "CERT_ANNUELS" for g in opts["types"] for t in g["types"])
    mid = _mission(client, a)
    d = client.get(f"/espace/missions/{mid}", headers=a).json()
    assert d["intitule"] == "Certification 2026" and d["client"]["raison_sociale"] == "Société Test SA"
    assert d["balance"]["nb_lignes"] == 0 and d["seuils"] is None and len(d["diligences"]) > 0
    did = d["diligences"][0]["id"]
    assert client.patch(f"/espace/missions/{mid}/diligences/{did}", headers=a).json()["fait"] is True
    assert client.get(f"/espace/missions/{mid}", headers=a).json()["diligences"][0]["fait"] is True


def test_un_cabinet_ne_voit_pas_la_mission_d_un_autre(client, deux_cabinets):
    a, b = deux_cabinets
    mid = _mission(client, a)
    # routes « espace »
    assert client.get(f"/espace/missions/{mid}", headers=b).status_code == 404
    assert client.patch(f"/espace/missions/{mid}/diligences/1", headers=b).status_code == 404
    # routes JSON historiques : lecture ET écriture refusées à l'autre cabinet
    for url in (f"/missions/{mid}/analyse-financiere", f"/missions/{mid}/seuils", f"/missions/{mid}/fraude/benford",
                f"/missions/{mid}/risques", f"/missions/{mid}/planification", f"/missions/{mid}/acceptation"):
        assert client.get(url, headers=b).status_code == 404, url
    assert client.post(f"/missions/{mid}/seuils", json={"resultat_net": 1}, headers=b).status_code == 404
    # le cabinet propriétaire, lui, passe (409 = aucune balance importée, donc la garde a laissé passer)
    assert client.get(f"/missions/{mid}/analyse-financiere", headers=a).status_code == 409


def test_client_d_un_autre_cabinet_refuse(client, deux_cabinets):
    a, b = deux_cabinets
    cid = client.post("/espace/clients", json={"raison_sociale": "Client de A"}, headers=a).json()["id"]
    r = client.post("/espace/missions", json={"client_id": cid, "intitule": "Intrusion"}, headers=b)
    assert r.status_code == 404


def test_referentiel_ou_type_inconnu_refuse(client, deux_cabinets):
    a, _ = deux_cabinets
    cid = client.post("/espace/clients", json={"raison_sociale": "Client"}, headers=a).json()["id"]
    assert client.post("/espace/missions", json={"client_id": cid, "intitule": "x1", "referentiel": "NOPE"}, headers=a).status_code == 422
    assert client.post("/espace/missions", json={"client_id": cid, "intitule": "x1", "type_mission": "NOPE"}, headers=a).status_code == 422
