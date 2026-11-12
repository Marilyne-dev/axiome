"""Phase 7 — veille réglementaire : amorçage, filtre, lu, saisie."""
from __future__ import annotations

from _helpers_ecrans import ck

from app.models.veille import VeilleReglementaire
from app.services import veille_service


def test_amorcage_et_filtre(client, db_session):
    c = ck(client)
    assert client.get("/vue/veille", cookies=c).status_code == 200
    client.post("/vue/veille/init", cookies=c, follow_redirects=False)
    total = db_session.query(VeilleReglementaire).count()
    assert total == 5
    # filtre PCG_FR -> inclut aussi TRANSVERSE
    pcg = veille_service.lister(db_session, "PCG_FR")
    refs = {v.referentiel for v in pcg}
    assert refs <= {"PCG_FR", "TRANSVERSE"} and "IFRS" not in refs


def test_marquer_lu_et_ajout(client, db_session):
    c = ck(client)
    client.post("/vue/veille/init", cookies=c, follow_redirects=False)
    v = db_session.query(VeilleReglementaire).first()
    client.post(f"/vue/veille/{v.id}/lu", cookies=c, data={"lu": "1"}, follow_redirects=False)
    db_session.expire_all()
    assert db_session.get(VeilleReglementaire, v.id).lu is True
    client.post("/vue/veille/add", cookies=c,
                data={"titre": "Note interne", "reference": "X1", "referentiel": "IFRS",
                      "impact": "fort", "resume": "test"}, follow_redirects=False)
    assert db_session.query(VeilleReglementaire).filter_by(titre="Note interne").count() == 1


def test_amorcage_idempotent(db_session):
    assert veille_service.amorcer(db_session) == 5
    assert veille_service.amorcer(db_session) == 0  # deuxième appel : rien
