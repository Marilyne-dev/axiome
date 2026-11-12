"""Phase 8 — feuille de travail éditable : rapprochement bancaire."""
from __future__ import annotations

from app.models.balance import LigneBalance
from app.models.cabinet import Cabinet
from app.models.client import Client
from app.models.mission import Mission
from app.models.rapprochement import RapprochementBancaire


def _cookies(client):
    return client.post("/login", data={"email": "admin@axiome.io", "password": "Test!2026"},
                       follow_redirects=False).cookies


def _mission_avec_balance(db):
    cab = Cabinet(nom="Cab"); db.add(cab); db.flush()
    cl = Client(cabinet_id=cab.id, raison_sociale="Alpha SAS"); db.add(cl); db.flush()
    m = Mission(client_id=cl.id, intitule="Audit Alpha", referentiel="PCG_FR",
                pays="France", devise="EUR"); db.add(m); db.flush()
    # 2 comptes bancaires/caisse + 1 compte trésorerie non bancaire (à exclure)
    db.add(LigneBalance(mission_id=m.id, compte="512000", libelle="Banque", cs_standard="TRESORERIE", solde_n=25000))
    db.add(LigneBalance(mission_id=m.id, compte="531000", libelle="Caisse", cs_standard="TRESORERIE", solde_n=800))
    db.add(LigneBalance(mission_id=m.id, compte="471000", libelle="Compte attente", cs_standard="TRESORERIE", solde_n=100))
    db.commit()
    return m.id


def test_init_filtre_comptes_bancaires(client, db_session):
    mid = _mission_avec_balance(db_session)
    ck = _cookies(client)
    client.post(f"/missions/{mid}/vue/rapprochement/init", cookies=ck, follow_redirects=False)
    rows = db_session.query(RapprochementBancaire).filter_by(mission_id=mid).all()
    assert {r.compte for r in rows} == {"512000", "531000"}  # 471 exclu
    # idempotent
    client.post(f"/missions/{mid}/vue/rapprochement/init", cookies=ck, follow_redirects=False)
    assert db_session.query(RapprochementBancaire).filter_by(mission_id=mid).count() == 2


def test_saisie_et_ecart(client, db_session):
    mid = _mission_avec_balance(db_session)
    ck = _cookies(client)
    client.post(f"/missions/{mid}/vue/rapprochement/init", cookies=ck, follow_redirects=False)
    banque = db_session.query(RapprochementBancaire).filter_by(mission_id=mid, compte="512000").first()
    # relevé à 24 500 -> écart 500, validé + commentaire
    client.post(f"/missions/{mid}/vue/rapprochement/save", cookies=ck,
                data={f"releve_{banque.id}": "24500", f"valide_{banque.id}": "on",
                      f"comm_{banque.id}": "chèque en suspens"}, follow_redirects=False)
    db_session.expire_all()
    b = db_session.get(RapprochementBancaire, banque.id)
    assert b.solde_releve == 24500 and b.ecart == 500 and b.valide is True
    assert b.commentaire == "chèque en suspens"


def test_page_affiche_cadrage(client, db_session):
    mid = _mission_avec_balance(db_session)
    ck = _cookies(client)
    client.post(f"/missions/{mid}/vue/rapprochement/init", cookies=ck, follow_redirects=False)
    r = client.get(f"/missions/{mid}/vue/rapprochement", cookies=ck)
    assert r.status_code == 200 and "Écart global" in r.text and "TOTAL" in r.text
