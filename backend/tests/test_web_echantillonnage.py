"""Phase 8 — écran échantillonnage (Module 11, NEP 530)."""
from __future__ import annotations

from _helpers_ecrans import ck, mission

from app.models.audit import Sample
from app.models.echantillonnage import SampleItem


def test_mus_item_conclusion(client, db_session):
    mid, cid = mission(db_session, avec_cycle=True)
    c = ck(client)
    assert client.get(f"/missions/{mid}/vue/echantillonnage", cookies=c).status_code == 200
    client.post(f"/missions/{mid}/vue/echantillonnage/cycle/{cid}/sample", cookies=c,
                data={"methode": "mus", "valeur_population": "100000",
                      "seuil_tolerable": "5000", "confiance": "0.95"}, follow_redirects=False)
    s = db_session.query(Sample).filter_by(cycle_id=cid).first()
    assert s.methode == "mus" and s.taille == 60  # 100000 * 3.0 / 5000
    client.post(f"/missions/{mid}/vue/echantillonnage/sample/{s.id}/item", cookies=c,
                data={"reference_piece": "FAC-001", "montant": "3200"}, follow_redirects=False)
    it = db_session.query(SampleItem).filter_by(sample_id=s.id).first()
    assert it.reference_piece == "FAC-001" and it.montant == 3200
    client.post(f"/missions/{mid}/vue/echantillonnage/item/{it.id}/conclusion", cookies=c,
                data={"conclusion": "anomalie"}, follow_redirects=False)
    db_session.expire_all()
    assert db_session.get(SampleItem, it.id).conclusion == "anomalie"
