"""Phase 8 — feuille de travail éditable : balance âgée clients/fournisseurs."""
from __future__ import annotations

from app.models.balance import LigneBalance
from app.models.balance_agee import BalanceAgee
from app.models.cabinet import Cabinet
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
    db.add(LigneBalance(mission_id=m.id, compte="411100", libelle="Client A",
                        cs_standard="CLIENTS ET COMPTES RATTACHES", solde_n=12000))
    db.add(LigneBalance(mission_id=m.id, compte="401100", libelle="Frs A",
                        cs_standard="FOURNISSEURS ET COMPTES RATTACHES", solde_n=5000))
    db.commit()
    return m.id


def test_init_cloisonne_clients_fournisseurs(client, db_session):
    mid = _mission(db_session)
    ck = _ck(client)
    client.post(f"/missions/{mid}/vue/balance-agee/clients/init", cookies=ck, follow_redirects=False)
    client.post(f"/missions/{mid}/vue/balance-agee/fournisseurs/init", cookies=ck, follow_redirects=False)
    clients = db_session.query(BalanceAgee).filter_by(mission_id=mid, cycle="CLIENTS").all()
    frs = db_session.query(BalanceAgee).filter_by(mission_id=mid, cycle="FOURNISSEURS").all()
    assert {r.compte for r in clients} == {"411100"}
    assert {r.compte for r in frs} == {"401100"}


def test_ventilation_et_ecart(client, db_session):
    mid = _mission(db_session)
    ck = _ck(client)
    client.post(f"/missions/{mid}/vue/balance-agee/clients/init", cookies=ck, follow_redirects=False)
    r = db_session.query(BalanceAgee).filter_by(mission_id=mid, cycle="CLIENTS").first()
    # ventilation complète : 5000 + 4000 + 3000 = 12000 -> écart 0
    client.post(f"/missions/{mid}/vue/balance-agee/clients/save", cookies=ck,
                data={f"non_echu_{r.id}": "5000", f"e60_{r.id}": "4000", f"eplus_{r.id}": "3000",
                      f"comm_{r.id}": "relance"}, follow_redirects=False)
    db_session.expire_all()
    b = db_session.get(BalanceAgee, r.id)
    assert b.total_ventile == 12000 and b.ecart == 0 and b.commentaire == "relance"


def test_cycle_invalide_404(client, db_session):
    mid = _mission(db_session)
    assert client.get(f"/missions/{mid}/vue/balance-agee/inexistant", cookies=_ck(client)).status_code == 404
