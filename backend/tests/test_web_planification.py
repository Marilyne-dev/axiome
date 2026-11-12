"""Phase 8 — écran planification (Module 3)."""
from __future__ import annotations

from _helpers_ecrans import ck, mission

from app.models.planification import Jalon, LigneBudget, PlanMission


def test_plan_jalon_budget(client, db_session):
    mid = mission(db_session)
    c = ck(client)
    assert client.get(f"/missions/{mid}/vue/planification", cookies=c).status_code == 200
    client.post(f"/missions/{mid}/vue/planification/save", cookies=c,
                data={"date_debut": "2026-01-05", "date_fin": "2026-03-31",
                      "approche": "mixte", "honoraires": "15000"}, follow_redirects=False)
    client.post(f"/missions/{mid}/vue/planification/jalon", cookies=c,
                data={"libelle": "Intérim", "echeance": "2026-02-01"}, follow_redirects=False)
    client.post(f"/missions/{mid}/vue/planification/budget", cookies=c,
                data={"poste": "Contrôle des comptes", "montant": "8000"}, follow_redirects=False)
    db_session.expire_all()
    plan = db_session.query(PlanMission).filter_by(mission_id=mid).first()
    assert plan.approche == "mixte" and plan.honoraires == 15000
    assert db_session.query(Jalon).filter_by(plan_id=plan.id).count() == 1
    assert db_session.query(LigneBudget).filter_by(plan_id=plan.id).first().montant == 8000
