"""Vérifications spécifiques : figures auto, concordance/écart, points, cloisonnement."""
from __future__ import annotations

from _helpers_ecrans import ck

from app.models.balance import LigneBalance
from app.models.cabinet import Cabinet
from app.models.client import Client
from app.models.mission import Mission
from app.models.verification import VerifConcordance, VerifPoint


def _mission_verif(client, db, intitule="Vérif"):
    cab = db.query(Cabinet).first()
    cl = Client(cabinet_id=cab.id, raison_sociale="Alpha SAS"); db.add(cl); db.commit()
    client.post("/vue/missions/creer", cookies=ck(client), follow_redirects=False, data={
        "client_id": cl.id, "intitule": intitule, "type_mission": "VERIF_SPEC"})
    return db.query(Mission).filter_by(intitule=intitule).first()


def _balance(db, mission_id):
    lignes = [("701000", 0, 500000, 0), ("601000", 0, 0, 420000),
              ("101000", -100000, 0, 0), ("211000", 300000, 0, 0),
              ("512000", 80000, 0, 0), ("411000", 120000, 0, 0)]
    for compte, sn, mc, md in lignes:
        db.add(LigneBalance(mission_id=mission_id, compte=compte, libelle=compte,
                            solde_n=sn, mvt_credit_n=mc, mvt_debit_n=md))
    db.commit()


def test_page_initialise_lignes_et_points(client, db_session):
    m = _mission_verif(client, db_session)
    page = client.get(f"/missions/{m.id}/vue/verifications", cookies=ck(client))
    assert page.status_code == 200
    assert db_session.query(VerifConcordance).filter_by(mission_id=m.id).count() == 5
    assert db_session.query(VerifPoint).filter_by(mission_id=m.id).count() == 6


def test_figures_auto_depuis_balance(client, db_session):
    m = _mission_verif(client, db_session, "Vérif figures")
    _balance(db_session, m.id)
    client.get(f"/missions/{m.id}/vue/verifications", cookies=ck(client))  # ensure rafraîchit
    ca = db_session.query(VerifConcordance).filter_by(mission_id=m.id, code="CA").first()
    cp = db_session.query(VerifConcordance).filter_by(mission_id=m.id, code="CP").first()
    bilan = db_session.query(VerifConcordance).filter_by(mission_id=m.id, code="BILAN").first()
    assert ca.montant_comptes == 500000.0
    assert cp.montant_comptes == 100000.0
    assert bilan.montant_comptes == 500000.0


def test_concordance_et_ecart(client, db_session):
    m = _mission_verif(client, db_session, "Vérif conc")
    _balance(db_session, m.id)
    client.get(f"/missions/{m.id}/vue/verifications", cookies=ck(client))
    client.post(f"/missions/{m.id}/vue/verifications/ligne/CA", cookies=ck(client),
                follow_redirects=False, data={"montant_rapport": "500 000"})
    client.post(f"/missions/{m.id}/vue/verifications/ligne/RES", cookies=ck(client),
                follow_redirects=False, data={"montant_rapport": "90000"})
    from app.services import verifications_service
    etat = verifications_service.etat(db_session, m.id)
    par_code = {le["code"]: le for le in etat["lignes"]}
    assert par_code["CA"]["statut"] == "concordant"
    assert par_code["RES"]["statut"] == "ecart" and par_code["RES"]["ecart"] == 10000.0
    assert etat["concordants"] == 1 and etat["ecarts"] == 1


def test_toggle_point(client, db_session):
    m = _mission_verif(client, db_session, "Vérif point")
    client.get(f"/missions/{m.id}/vue/verifications", cookies=ck(client))
    p = db_session.query(VerifPoint).filter_by(mission_id=m.id, code="RG_CONC").first()
    assert p.fait is False
    client.post(f"/missions/{m.id}/vue/verifications/point/RG_CONC/toggle", cookies=ck(client),
                follow_redirects=False)
    db_session.refresh(p)
    assert p.fait is True


def test_verifications_cloisonnement(client, db_session):
    autre = Cabinet(nom="Autre"); db_session.add(autre); db_session.flush()
    cl = Client(cabinet_id=autre.id, raison_sociale="Hors"); db_session.add(cl); db_session.flush()
    m = Mission(client_id=cl.id, intitule="Hors", type_mission="VERIF_SPEC",
                referentiel="PCG_FR", devise="EUR", pays="France")
    db_session.add(m); db_session.commit()
    assert client.get(f"/missions/{m.id}/vue/verifications",
                      cookies=ck(client)).status_code == 403
