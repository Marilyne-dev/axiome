"""Phase 8 — écran acceptation (Module 1)."""
from __future__ import annotations

from _helpers_ecrans import ck, mission

from app.models.acceptation import Acceptation, LettreMission
from app.models.mission import Mission


def test_garde_fou_conflit_puis_acceptation(client, db_session):
    mid = mission(db_session)
    c = ck(client)
    assert client.get(f"/missions/{mid}/vue/acceptation", cookies=c).status_code == 200
    # conflit coché -> acceptation refusée par le garde-fou
    client.post(f"/missions/{mid}/vue/acceptation/save", cookies=c,
                data={"conflit_interet": "on", "niveau_risque_global": "eleve"}, follow_redirects=False)
    client.post(f"/missions/{mid}/vue/acceptation/decision", cookies=c,
                data={"decision": "acceptee", "motivation": "x"}, follow_redirects=False)
    db_session.expire_all()
    acc = db_session.query(Acceptation).filter_by(mission_id=mid).first()
    assert acc.decision == "en_cours"  # bloqué
    # conflit levé -> acceptation ok + mission planifiée
    client.post(f"/missions/{mid}/vue/acceptation/save", cookies=c,
                data={"independance_ok": "on", "kyc_ok": "on"}, follow_redirects=False)
    client.post(f"/missions/{mid}/vue/acceptation/decision", cookies=c,
                data={"decision": "acceptee", "motivation": "dossier conforme"}, follow_redirects=False)
    db_session.expire_all()
    acc = db_session.query(Acceptation).filter_by(mission_id=mid).first()
    assert acc.decision == "acceptee" and acc.motivation == "dossier conforme"
    assert db_session.get(Mission, mid).statut == "planification"
    # lettre de mission générée
    client.post(f"/missions/{mid}/vue/acceptation/lettre", cookies=c, follow_redirects=False)
    assert db_session.query(LettreMission).filter_by(acceptation_id=acc.id).first() is not None
