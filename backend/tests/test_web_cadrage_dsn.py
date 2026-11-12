"""Phase 8 — feuille de travail éditable : cadrage FEC / DSN (Personnel)."""
from __future__ import annotations

from app.models.balance import LigneBalance
from app.models.cabinet import Cabinet
from app.models.cadrage_dsn import LigneCadrageDSN
from app.models.client import Client
from app.models.mission import Mission


def _ck(client):
    return client.post("/login", data={"email": "admin@axiome.io", "password": "Test!2026"},
                       follow_redirects=False).cookies


def _mission(db):
    cab = Cabinet(nom="Cab"); db.add(cab); db.flush()
    cl = Client(cabinet_id=cab.id, raison_sociale="Alpha"); db.add(cl); db.flush()
    m = Mission(client_id=cl.id, intitule="Audit", referentiel="PCG_FR",
                pays="France", devise="EUR"); db.add(m); db.flush()
    db.add(LigneBalance(mission_id=m.id, compte="641100", libelle="Rémunérations", solde_n=120000))
    db.add(LigneBalance(mission_id=m.id, compte="645100", libelle="Cotisations URSSAF", solde_n=48000))
    db.add(LigneBalance(mission_id=m.id, compte="411000", libelle="Clients", solde_n=9000))
    db.commit()
    return m.id


def test_init_ne_retient_que_les_comptes_64(client, db_session):
    mid = _mission(db_session)
    client.post(f"/missions/{mid}/vue/cadrage-dsn/init", cookies=_ck(client), follow_redirects=False)
    rows = db_session.query(LigneCadrageDSN).filter_by(mission_id=mid).all()
    assert {r.compte for r in rows} == {"641100", "645100"}


def test_saisie_dsn_et_ecart(client, db_session):
    mid = _mission(db_session)
    ck = _ck(client)
    client.post(f"/missions/{mid}/vue/cadrage-dsn/init", cookies=ck, follow_redirects=False)
    r = db_session.query(LigneCadrageDSN).filter_by(compte="641100").first()
    client.post(f"/missions/{mid}/vue/cadrage-dsn/save", cookies=ck,
                data={f"dsn_{r.id}": "118000", f"comm_{r.id}": "écart primes"}, follow_redirects=False)
    db_session.expire_all()
    b = db_session.get(LigneCadrageDSN, r.id)
    assert b.montant_dsn == 118000 and b.ecart == 2000 and b.commentaire == "écart primes"


def test_page_affiche_cadrage(client, db_session):
    mid = _mission(db_session)
    ck = _ck(client)
    client.post(f"/missions/{mid}/vue/cadrage-dsn/init", cookies=ck, follow_redirects=False)
    r = client.get(f"/missions/{mid}/vue/cadrage-dsn", cookies=ck)
    assert r.status_code == 200 and "Cadrage FEC / DSN" in r.text and "641100" in r.text
