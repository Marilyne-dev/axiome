"""Phase 8 — écran confirmations externes (Module 12, NEP 505)."""
from __future__ import annotations

from _helpers_ecrans import ck, mission

from app.models.audit import Confirmation


def test_add_et_statut(client, db_session):
    mid = mission(db_session)
    c = ck(client)
    client.post(f"/missions/{mid}/vue/confirmations/add", cookies=c,
                data={"tiers": "Banque X", "type_tiers": "banque"}, follow_redirects=False)
    conf = db_session.query(Confirmation).filter_by(mission_id=mid).first()
    assert conf.tiers == "Banque X" and conf.statut == "envoyee"
    client.post(f"/missions/{mid}/vue/confirmations/{conf.id}/statut", cookies=c,
                data={"statut": "recue"}, follow_redirects=False)
    db_session.expire_all()
    assert db_session.get(Confirmation, conf.id).statut == "recue"
    page = client.get(f"/missions/{mid}/vue/confirmations", cookies=c)
    assert page.status_code == 200 and "Banque X" in page.text
