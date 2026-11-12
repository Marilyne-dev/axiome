"""Phase 6 — dashboard de pilotage (indicateurs transversaux)."""
from __future__ import annotations

from app.models.audit import RiskItem
from app.models.cabinet import Cabinet
from app.models.client import Client
from app.models.conclusion import CycleConclusion
from app.models.mission import Cycle, Mission
from app.services.pilotage_service import synthese


def _ck(client):
    return client.post("/login", data={"email": "admin@axiome.io", "password": "Test!2026"},
                       follow_redirects=False).cookies


def _mission(db, ref="PCG_FR", cabinet_admin=False):
    # cabinet_admin=True : la mission appartient au cabinet de l'utilisateur connecté (cloisonnement).
    cab = db.query(Cabinet).first() if cabinet_admin else Cabinet(nom="Cab")
    if not cabinet_admin:
        db.add(cab)
    db.flush()
    cl = Client(cabinet_id=cab.id, raison_sociale="Alpha"); db.add(cl); db.flush()
    m = Mission(client_id=cl.id, intitule="Audit Alpha", referentiel=ref,
                pays="France", devise="EUR"); db.add(m); db.flush()
    db.add(Cycle(mission_id=m.id, code="TRESORERIE", libelle="Trésorerie"))
    db.commit()
    return m.id


def test_synthese_service(db_session):
    mid = _mission(db_session)
    db_session.add(RiskItem(mission_id=mid, libelle="Fraude", categorie="fraude",
                            probabilite=5, impact=5))
    db_session.add(CycleConclusion(mission_id=mid, cycle_code="TRESORERIE",
                                   conclusion="Écart", anomalie=True))
    db_session.commit()
    s = synthese(db_session)
    assert s["nb_missions"] == 1
    assert s["risques_par_niveau"]["critique"] == 1
    assert s["missions_avec_anomalies"] == 1
    assert s["lignes"][0]["avancement"] == 100  # 1 conclusion / 1 cycle


def test_page_pilotage(client, db_session):
    _mission(db_session, ref="SYSCOHADA_OHADA", cabinet_admin=True)
    r = client.get("/vue/pilotage", cookies=_ck(client))
    assert r.status_code == 200
    assert "Pilotage du cabinet" in r.text and "SYSCOHADA_OHADA" in r.text
    assert "Avancement par mission" in r.text
