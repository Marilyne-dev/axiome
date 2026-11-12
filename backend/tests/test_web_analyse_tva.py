"""Phase 8 — feuille de travail éditable : cadrage TVA collectée (Impôts)."""
from __future__ import annotations

from app.models.analyse_tva import LigneTVA
from app.models.balance import LigneBalance
from app.models.cabinet import Cabinet
from app.models.client import Client
from app.models.mission import Mission


def _ck(client):
    return client.post("/login", data={"email": "admin@axiome.io", "password": "Test!2026"},
                       follow_redirects=False).cookies


def _mission(db, referentiel="PCG_FR", pays="France"):
    cab = Cabinet(nom="Cab"); db.add(cab); db.flush()
    cl = Client(cabinet_id=cab.id, raison_sociale="Alpha"); db.add(cl); db.flush()
    m = Mission(client_id=cl.id, intitule="Audit", referentiel=referentiel,
                pays=pays, devise="EUR"); db.add(m); db.flush()
    db.add(LigneBalance(mission_id=m.id, compte="445710", libelle="TVA collectée", solde_n=20000))
    db.commit()
    return m.id


def test_init_taux_metropole_et_prefill_4457(client, db_session):
    mid = _mission(db_session)
    client.post(f"/missions/{mid}/vue/analyse-tva/init", cookies=_ck(client), follow_redirects=False)
    rows = db_session.query(LigneTVA).filter_by(mission_id=mid).order_by(LigneTVA.id).all()
    assert len(rows) == 4  # 20 / 10 / 5.5 / 2.1
    assert rows[0].taux == 0.20 and rows[0].tva_comptabilisee == 20000


def test_init_taux_ohada(client, db_session):
    mid = _mission(db_session, referentiel="SYSCOHADA_OHADA", pays="Bénin")
    client.post(f"/missions/{mid}/vue/analyse-tva/init", cookies=_ck(client), follow_redirects=False)
    rows = db_session.query(LigneTVA).filter_by(mission_id=mid).all()
    assert len(rows) == 1 and rows[0].taux == 0.18


def test_saisie_base_calcule_theorique_et_ecart(client, db_session):
    mid = _mission(db_session)
    ck = _ck(client)
    client.post(f"/missions/{mid}/vue/analyse-tva/init", cookies=ck, follow_redirects=False)
    r = db_session.query(LigneTVA).filter_by(mission_id=mid).order_by(LigneTVA.id).first()
    # base 100000 × 20 % = 20000 -> théorique 20000, comptabilisée 20000 -> écart 0
    client.post(f"/missions/{mid}/vue/analyse-tva/save", cookies=ck,
                data={f"base_{r.id}": "100000", f"taux_{r.id}": "20",
                      f"tvac_{r.id}": "20000"}, follow_redirects=False)
    db_session.expire_all()
    b = db_session.get(LigneTVA, r.id)
    assert b.taux == 0.20 and b.tva_theorique == 20000 and b.ecart == 0
