"""Modules 6 & 15 — analyse financière et revue analytique."""
from __future__ import annotations

from app.models.balance import LigneBalance
from app.models.cabinet import Cabinet
from app.models.client import Client
from app.models.mission import Mission
from app.services.analyse_service import agregats, ratios
from app.services.revue_service import revue_analytique


def _mission_avec_balance(db):
    cab = Cabinet(nom="C"); db.add(cab); db.flush()
    cl = Client(cabinet_id=cab.id, raison_sociale="Kappa"); db.add(cl); db.flush()
    m = Mission(client_id=cl.id, intitule="M", referentiel="PCG_FR", pays="France", devise="EUR")
    db.add(m); db.flush()
    donnees = [
        ("101000", "Capital", 100000, 100000),
        ("164000", "Emprunts", 40000, 60000),
        ("213000", "Constructions", 90000, 95000),
        ("370000", "Stocks", 20000, 18000),
        ("411000", "Clients", 30000, 25000),
        ("401000", "Fournisseurs", 15000, 12000),
        ("512000", "Banque", 25000, 20000),
    ]
    for cpte, lib, sn, sn1 in donnees:
        db.add(LigneBalance(mission_id=m.id, compte=cpte, libelle=lib, cs_standard="", solde_n=sn, solde_n1=sn1))
    db.commit()
    return m.id


def test_agregats_frng_bfr(db_session):
    mid = _mission_avec_balance(db_session)
    lignes = db_session.query(LigneBalance).filter_by(mission_id=mid).all()
    a = agregats(lignes)
    # Ressources durables = CP(100k)+emprunts(40k)=140k ; emplois=immo(90k) -> FRNG=50k
    assert a["ressources_durables"] == 140000.0
    assert a["fonds_de_roulement_net_global"] == 50000.0
    # BFR = (stocks 20k + clients 30k) - (frs 15k) = 35k
    assert a["besoin_en_fonds_de_roulement"] == 35000.0
    assert a["tresorerie_nette"] == 15000.0  # FRNG - BFR


def test_ratios(db_session):
    mid = _mission_avec_balance(db_session)
    lignes = db_session.query(LigneBalance).filter_by(mission_id=mid).all()
    r = ratios(lignes)
    assert r["couverture_immobilisations"] is not None
    assert r["autonomie_financiere"] is not None


def test_revue_analytique_seuil(db_session):
    mid = _mission_avec_balance(db_session)
    lignes = db_session.query(LigneBalance).filter_by(mission_id=mid).all()
    rev = revue_analytique(lignes, seuil=15000)
    # L'emprunt varie de -20 000 (>= 15 000) -> significatif
    ligne_emp = next(l for l in rev["lignes"] if l["compte"] == "164000")
    assert ligne_emp["variation"] == -20000.0 and ligne_emp["significatif"] is True
    assert rev["nb_significatifs"] >= 1


def test_endpoint_analyse_sans_balance(client, db_session):
    cab = Cabinet(nom="C"); db_session.add(cab); db_session.flush()
    cl = Client(cabinet_id=cab.id, raison_sociale="Z"); db_session.add(cl); db_session.flush()
    m = Mission(client_id=cl.id, intitule="M", referentiel="PCG_FR", pays="France", devise="EUR")
    db_session.add(m); db_session.commit()
    tok = client.post("/auth/login", json={"email": "admin@axiome.io", "password": "Test!2026"}).json()["access_token"]
    r = client.get(f"/missions/{m.id}/analyse-financiere", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 409  # pas de balance -> conflit explicite
