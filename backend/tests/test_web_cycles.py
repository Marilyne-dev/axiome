"""Phase 8 — écran détail de cycle : programme de travail + contrôle interne."""
from __future__ import annotations

from app.models.cabinet import Cabinet
from app.models.client import Client
from app.models.controle_interne import ControleInterne
from app.models.mission import Cycle, Mission
from app.models.programme import ProcedureAudit


def _cookies(client):
    return client.post("/login", data={"email": "admin@axiome.io", "password": "Test!2026"},
                       follow_redirects=False).cookies


def _mission_cycle(db):
    cab = Cabinet(nom="Cab"); db.add(cab); db.flush()
    cl = Client(cabinet_id=cab.id, raison_sociale="Alpha SAS"); db.add(cl); db.flush()
    m = Mission(client_id=cl.id, intitule="Audit Alpha", referentiel="PCG_FR",
                pays="France", devise="EUR"); db.add(m); db.flush()
    cy = Cycle(mission_id=m.id, code="TRESORERIE", libelle="Trésorerie"); db.add(cy); db.commit()
    return m.id, cy.id


def test_cycles_liste_et_detail(client, db_session):
    mid, cid = _mission_cycle(db_session)
    ck = _cookies(client)
    assert client.get(f"/missions/{mid}/vue/cycles", cookies=ck).status_code == 200
    assert client.get(f"/missions/{mid}/vue/cycles/{cid}", cookies=ck).status_code == 200


def test_generer_programme_et_cocher(client, db_session):
    mid, cid = _mission_cycle(db_session)
    ck = _cookies(client)
    client.post(f"/missions/{mid}/vue/cycles/{cid}/programme", cookies=ck, follow_redirects=False)
    procs = db_session.query(ProcedureAudit).all()
    assert len(procs) == 3  # modèle TRESORERIE
    # idempotent : re-générer n'ajoute rien
    client.post(f"/missions/{mid}/vue/cycles/{cid}/programme", cookies=ck, follow_redirects=False)
    assert db_session.query(ProcedureAudit).count() == 3
    # cocher
    pid = procs[0].id
    client.post(f"/missions/{mid}/vue/cycles/{cid}/procedures/{pid}/toggle", cookies=ck, follow_redirects=False)
    db_session.expire_all()
    assert db_session.get(ProcedureAudit, pid).fait is True


def test_ajouter_controle_interne(client, db_session):
    mid, cid = _mission_cycle(db_session)
    ck = _cookies(client)
    r = client.post(f"/missions/{mid}/vue/cycles/{cid}/controle", cookies=ck,
                    data={"intitule": "Séparation des tâches", "composante_coso": "activites_controle",
                          "conclusion": "deficient"}, follow_redirects=False)
    assert r.status_code == 302
    ci = db_session.query(ControleInterne).filter_by(cycle_id=cid).first()
    assert ci is not None and ci.conclusion == "deficient"
