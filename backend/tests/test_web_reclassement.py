"""Écran mission — reclassement manuel d'un compte vers un autre cycle."""
from __future__ import annotations

from _helpers_ecrans import ck, mission

from app.core.cycles_ref import cycle_pour_cs
from app.models.balance import LigneBalance


def test_reclasser_un_compte(client, db_session):
    mid = mission(db_session)
    # Compte classé AUTRES à corriger.
    db_session.add(LigneBalance(mission_id=mid, compte="606000", libelle="Fournitures",
                                cs_standard="AUTRES COMPTES", solde_n=1500, solde_n1=0))
    db_session.commit()
    lid = db_session.query(LigneBalance).filter_by(mission_id=mid).first().id

    page = client.get(f"/missions/{mid}/vue/reclassement", cookies=ck(client))
    assert page.status_code == 200 and "606000" in page.text

    r = client.post(f"/missions/{mid}/vue/reclassement/{lid}", data={"cycle": "STOCKS"},
                    cookies=ck(client), follow_redirects=False)
    assert r.status_code == 302
    db_session.expire_all()
    lb = db_session.get(LigneBalance, lid)
    assert cycle_pour_cs(lb.cs_standard) == "STOCKS"


def test_reclasser_cycle_invalide_ignore(client, db_session):
    mid = mission(db_session)
    db_session.add(LigneBalance(mission_id=mid, compte="512000", libelle="Banque",
                                cs_standard="TRESORERIE", solde_n=1000, solde_n1=0))
    db_session.commit()
    lid = db_session.query(LigneBalance).filter_by(mission_id=mid).first().id
    client.post(f"/missions/{mid}/vue/reclassement/{lid}", data={"cycle": "INEXISTANT"},
                cookies=ck(client), follow_redirects=False)
    db_session.expire_all()
    lb = db_session.get(LigneBalance, lid)
    assert cycle_pour_cs(lb.cs_standard) == "TRESORERIE"  # inchangé


def test_reclassement_en_masse(client, db_session):
    mid = mission(db_session)
    for cpte in ("601000", "606000", "607000"):
        db_session.add(LigneBalance(mission_id=mid, compte=cpte, libelle="Achat",
                                    cs_standard="AUTRES COMPTES", solde_n=100, solde_n1=0))
    db_session.add(LigneBalance(mission_id=mid, compte="512000", libelle="Banque",
                                cs_standard="TRESORERIE", solde_n=50, solde_n1=0))
    db_session.commit()
    r = client.post(f"/missions/{mid}/vue/reclassement/masse",
                    data={"prefixe": "60", "cycle": "STOCKS"},
                    cookies=ck(client), follow_redirects=False)
    assert r.status_code == 302 and "masse=3" in r.headers["location"]
    db_session.expire_all()
    cycles = {lb.compte: cycle_pour_cs(lb.cs_standard)
              for lb in db_session.query(LigneBalance).filter_by(mission_id=mid).all()}
    assert cycles["601000"] == cycles["606000"] == cycles["607000"] == "STOCKS"
    assert cycles["512000"] == "TRESORERIE"  # hors préfixe : inchangé
