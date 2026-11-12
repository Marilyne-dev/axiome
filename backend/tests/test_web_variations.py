"""Écran mission — panneau des variations significatives (revue analytique)."""
from __future__ import annotations

from _helpers_ecrans import ck, mission

from app.models.audit import Threshold
from app.models.balance import LigneBalance


def _garnir(db, mid):
    db.add(LigneBalance(mission_id=mid, compte="601000", libelle="Achats",
                        cs_standard="AUTRES COMPTES", solde_n=50000, solde_n1=10000))
    db.add(LigneBalance(mission_id=mid, compte="606000", libelle="Petit",
                        cs_standard="AUTRES COMPTES", solde_n=1100, solde_n1=1000))
    db.add(Threshold(mission_id=mid, seuil_signification=5000, seuil_planification=3500,
                     seuil_remontee=250, base_retenue="resultat_net"))
    db.commit()


def test_panneau_variations_filtre_par_seuil(client, db_session):
    mid = mission(db_session)
    _garnir(db_session, mid)
    t = client.get(f"/missions/{mid}/vue", cookies=ck(client)).text
    assert "Variations significatives" in t
    assert "601000" in t          # variation 40000 > seuil 5000
    assert "606000" not in t       # variation 100 < seuil


def test_pas_de_panneau_variations_sans_seuil(client, db_session):
    mid = mission(db_session)
    db_session.add(LigneBalance(mission_id=mid, compte="601000", libelle="Achats",
                                cs_standard="AUTRES COMPTES", solde_n=50000, solde_n1=10000))
    db_session.commit()
    # Sans seuil de signification, le panneau ne s'affiche pas.
    t = client.get(f"/missions/{mid}/vue", cookies=ck(client)).text
    assert "Variations significatives" not in t
