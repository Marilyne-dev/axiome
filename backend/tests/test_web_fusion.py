"""Commissariat à la fusion : moteur de parité, contrôles, rapport, cloisonnement."""
from __future__ import annotations

from _helpers_ecrans import ck

from app.models.cabinet import Cabinet
from app.models.client import Client
from app.models.edition import RapportEdition
from app.models.fusion import FusionDossier, FusionEvaluation
from app.models.mission import Mission
from app.services import fusion_service


def _mission_fusion(client, db, intitule="Fusion"):
    cab = db.query(Cabinet).first()
    cl = Client(cabinet_id=cab.id, raison_sociale="Alpha SA"); db.add(cl); db.commit()
    client.post("/vue/missions/creer", cookies=ck(client), follow_redirects=False, data={
        "client_id": cl.id, "intitule": intitule, "type_mission": "FUSION_APPORT"})
    return db.query(Mission).filter_by(intitule=intitule).first()


def _remplir(client, m, num="4", den="5", vn="50"):
    client.post(f"/missions/{m.id}/vue/fusion/dossier", cookies=ck(client), follow_redirects=False, data={
        "nom_absorbante": "Alpha SA", "nom_absorbee": "Beta SAS",
        "actions_absorbante": "100000", "actions_absorbee": "50000",
        "valeur_nominale": vn, "parite_num": num, "parite_den": den})
    for soc, meth, val in [("A", "ANC", "9500000"), ("A", "ANR", "10500000"),
                           ("B", "ANC", "3800000"), ("B", "DCF", "4200000")]:
        client.post(f"/missions/{m.id}/vue/fusion/evaluation", cookies=ck(client),
                    follow_redirects=False, data={"societe": soc, "methode": meth, "valeur": val})


def test_page_cree_dossier(client, db_session):
    m = _mission_fusion(client, db_session)
    assert client.get(f"/missions/{m.id}/vue/fusion", cookies=ck(client)).status_code == 200
    assert db_session.query(FusionDossier).filter_by(mission_id=m.id).count() == 1


def test_moteur_parite(client, db_session):
    m = _mission_fusion(client, db_session, "Fusion parité")
    _remplir(client, m)
    e = fusion_service.etat(db_session, m.id)
    assert e["valeur_a"] == 10000000.0 and e["valeur_b"] == 4000000.0
    assert e["vu_a"] == 100.0 and e["vu_b"] == 80.0
    assert e["parite_theorique"] == 0.8 and e["parite_retenue"] == 0.8
    assert e["actions_creees"] == 40000
    assert e["augmentation_capital"] == 2000000.0 and e["prime_fusion"] == 2000000.0
    assert e["controle_apport"] is True and e["alertes"] == []


def test_ecart_parite_alerte(client, db_session):
    m = _mission_fusion(client, db_session, "Fusion écart")
    _remplir(client, m, num="1", den="1")  # parité 1 vs théorique 0.8 => +25%
    e = fusion_service.etat(db_session, m.id)
    assert e["ecart"] is not None and abs(e["ecart"]) > e["seuil_ecart"]
    assert any("Parité retenue" in a for a in e["alertes"])


def test_apport_insuffisant_alerte(client, db_session):
    m = _mission_fusion(client, db_session, "Fusion apport")
    _remplir(client, m, vn="200")  # aug capital 40000*200=8M > actif net apporté 4M
    e = fusion_service.etat(db_session, m.id)
    assert e["controle_apport"] is False
    assert any("Actif net apporté inférieur" in a for a in e["alertes"])


def test_supprimer_evaluation(client, db_session):
    m = _mission_fusion(client, db_session, "Fusion suppr")
    _remplir(client, m)
    ev = db_session.query(FusionEvaluation).filter_by(mission_id=m.id, societe="A").first()
    client.post(f"/missions/{m.id}/vue/fusion/evaluation/{ev.id}/supprimer",
                cookies=ck(client), follow_redirects=False)
    assert db_session.get(FusionEvaluation, ev.id) is None


def test_rapport_fusion(client, db_session):
    m = _mission_fusion(client, db_session, "Fusion rapport")
    _remplir(client, m)
    d = client.get(f"/missions/{m.id}/vue/fusion/rapport?format=docx", cookies=ck(client))
    assert d.status_code == 200 and d.content[:2] == b"PK"
    p = client.get(f"/missions/{m.id}/vue/fusion/rapport?format=pdf", cookies=ck(client))
    assert p.status_code == 200 and p.content[:4] == b"%PDF"
    assert db_session.query(RapportEdition).filter_by(
        mission_id=m.id, type_edition="rapport-fusion").count() == 2


def test_fusion_cloisonnement(client, db_session):
    autre = Cabinet(nom="Autre"); db_session.add(autre); db_session.flush()
    cl = Client(cabinet_id=autre.id, raison_sociale="Hors"); db_session.add(cl); db_session.flush()
    m = Mission(client_id=cl.id, intitule="Hors", type_mission="FUSION_APPORT",
                referentiel="PCG_FR", devise="EUR", pays="France")
    db_session.add(m); db_session.commit()
    assert client.get(f"/missions/{m.id}/vue/fusion", cookies=ck(client)).status_code == 403
    assert client.get(f"/missions/{m.id}/vue/fusion/rapport?format=docx",
                      cookies=ck(client)).status_code == 403
