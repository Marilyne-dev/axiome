"""Écran mission — panneau des contrôles automatiques + bandeau d'alerte."""
from __future__ import annotations

from _helpers_ecrans import ck, mission

from app.models.balance import LigneBalance


def test_panneau_controles_alerte(client, db_session):
    mid = mission(db_session)
    # Balance délibérément hors bouclage et déséquilibrée.
    db_session.add(LigneBalance(mission_id=mid, compte="512000", libelle="Banque",
                                cs_standard="TRESORERIE", solde_n=1200, solde_n1=1000,
                                mvt_debit_n=300, mvt_credit_n=0))
    db_session.commit()
    r = client.get(f"/missions/{mid}/vue", cookies=ck(client))
    assert r.status_code == 200
    assert "Contrôles automatiques (balance)" in r.text
    assert "contrôle(s) automatique(s) en échec" in r.text   # bandeau d'alerte
    assert "Anomalie" in r.text


def test_pas_de_panneau_sans_balance(client, db_session):
    mid = mission(db_session)
    r = client.get(f"/missions/{mid}/vue", cookies=ck(client))
    assert r.status_code == 200
    # Sans balance : ni panneau ni bandeau d'alerte.
    assert "Contrôles automatiques (balance)" not in r.text
    assert "contrôle(s) automatique(s) en échec" not in r.text
