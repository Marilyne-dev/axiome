"""API JSON — import FEC (avec garde-fou) et suivi des circularisations (reçue / suppression)."""
from __future__ import annotations

import pytest

from app.models.balance import LigneBalance
from app.models.cabinet import Cabinet
from app.models.client import Client
from app.models.mission import Mission
from app.models.user import User

_COLS = ("JournalCode", "JournalLib", "EcritureNum", "EcritureDate", "CompteNum", "CompteLib", "CompAuxNum",
         "CompAuxLib", "PieceRef", "PieceDate", "EcritureLib", "Debit", "Credit", "EcritureLet", "DateLet",
         "ValidDate", "Montantdevise", "Idevise")


def _fec(*lignes: tuple[str, str, str, str]) -> bytes:
    """Construit un FEC minimal tabulé : (compte, libellé, débit, crédit)."""
    rows = ["\t".join(_COLS)]
    for compte, lib, debit, credit in lignes:
        d = {c: "" for c in _COLS}
        d.update(CompteNum=compte, CompteLib=lib, Debit=debit, Credit=credit, EcritureDate="20251231")
        rows.append("\t".join(d[c] for c in _COLS))
    return "\n".join(rows).encode("utf-8")


FEC_OK = _fec(("512000", "Banque", "10000,00", "0,00"), ("101000", "Capital", "0,00", "10000,00"),
              ("707000", "Ventes", "0,00", "2000,00"), ("411000", "Clients", "2000,00", "0,00"))


def _headers(client):
    tok = client.post("/auth/login", json={"email": "admin@axiome.io", "password": "Test!2026"}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def _mission(db, autre_cabinet: bool = False) -> int:
    """Mission rattachée au cabinet de l'utilisateur de test (ou à un autre cabinet : cloisonnement)."""
    if autre_cabinet:
        cab = Cabinet(nom="Autre cabinet", pays="France"); db.add(cab); db.flush(); cab_id = cab.id
    else:
        cab_id = db.query(User).filter_by(email="admin@axiome.io").one().cabinet_id
    cli = Client(cabinet_id=cab_id, raison_sociale="Theta", pays="France"); db.add(cli); db.flush()
    m = Mission(client_id=cli.id, intitule="M Theta", referentiel="PCG_FR", pays="France", devise="EUR")
    db.add(m); db.commit()
    return m.id


def _post_fec(client, h, mid, contenu, nom="123456789FEC20251231.txt", confirmer=None):
    params = {"confirmer": "true"} if confirmer else {}
    return client.post(f"/missions/{mid}/import/fec", headers=h, params=params,
                       files={"fichier": (nom, contenu, "text/plain")})


# ---------------------------------------------------------------- import FEC

def test_import_fec_cree_la_balance(client, db_session):
    h = _headers(client); mid = _mission(db_session)
    r = _post_fec(client, h, mid, FEC_OK)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["nb_comptes"] == 4 and j["equilibre"] is True and j["chiffre_affaires"] == 2000.0
    assert db_session.query(LigneBalance).filter_by(mission_id=mid).count() == 4


def test_import_fec_refuse_d_ecraser_sans_confirmation(client, db_session):
    h = _headers(client); mid = _mission(db_session)
    assert _post_fec(client, h, mid, FEC_OK).status_code == 200
    autre = _fec(("606000", "Achats", "500,00", "0,00"), ("401000", "Fournisseurs", "0,00", "500,00"))
    r = _post_fec(client, h, mid, autre)
    assert r.status_code == 409
    assert db_session.query(LigneBalance).filter_by(mission_id=mid).count() == 4      # rien n'a été touché
    assert _post_fec(client, h, mid, autre, confirmer=True).status_code == 200
    assert db_session.query(LigneBalance).filter_by(mission_id=mid).count() == 2


def test_import_fec_illisible_ne_detruit_pas_la_balance(client, db_session):
    h = _headers(client); mid = _mission(db_session)
    assert _post_fec(client, h, mid, FEC_OK).status_code == 200
    r = _post_fec(client, h, mid, b"ceci n'est pas un FEC\nloin de la", confirmer=True)
    assert r.status_code == 422
    assert db_session.query(LigneBalance).filter_by(mission_id=mid).count() == 4


def test_import_fec_mauvais_format(client, db_session):
    h = _headers(client); mid = _mission(db_session)
    assert _post_fec(client, h, mid, FEC_OK, nom="releve.pdf").status_code == 422


def test_import_fec_encodage_latin1(client, db_session):
    h = _headers(client); mid = _mission(db_session)
    fec = _fec(("512000", "Banque Société Générale", "100,00", "0,00"), ("101000", "Capital", "0,00", "100,00"))
    r = _post_fec(client, h, mid, fec.decode("utf-8").encode("latin-1"))
    assert r.status_code == 200 and r.json()["nb_comptes"] == 2


@pytest.mark.cloisonnement
def test_import_fec_cloisonne_par_cabinet(client, db_session):
    h = _headers(client); autre = _mission(db_session, autre_cabinet=True)
    assert _post_fec(client, h, autre, FEC_OK).status_code == 404


# ---------------------------------------------------------------- circularisation

def test_circularisation_cycle_complet(client, db_session):
    h = _headers(client); mid = _mission(db_session)
    cid = client.post(f"/missions/{mid}/confirmations", headers=h,
                      json={"tiers": "BNP Paribas", "type_tiers": "banque"}).json()["id"]
    lst = client.get(f"/missions/{mid}/confirmations", headers=h).json()
    assert lst[0]["statut"] == "envoyee" and lst[0]["cree_le"]
    assert client.post(f"/missions/{mid}/confirmations/{cid}/relancer", headers=h).json()["statut"] == "relancee"
    assert client.post(f"/missions/{mid}/confirmations/{cid}/recue", headers=h).json()["statut"] == "recue"
    assert client.post(f"/missions/{mid}/confirmations/{cid}/relancer", headers=h).status_code == 409
    assert client.delete(f"/missions/{mid}/confirmations/{cid}", headers=h).status_code == 204
    assert client.get(f"/missions/{mid}/confirmations", headers=h).json() == []


def test_circularisation_confirmation_d_une_autre_mission(client, db_session):
    h = _headers(client); m1 = _mission(db_session); m2 = _mission(db_session)
    cid = client.post(f"/missions/{m1}/confirmations", headers=h, json={"tiers": "X", "type_tiers": "client"}).json()["id"]
    assert client.post(f"/missions/{m2}/confirmations/{cid}/recue", headers=h).status_code == 404
    assert client.delete(f"/missions/{m2}/confirmations/{cid}", headers=h).status_code == 404
