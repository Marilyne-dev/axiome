"""Phase 7 — contenu normatif par référentiel + page dédiée."""
from __future__ import annotations

from app.core.referentiels_contenu import (
    CORRESPONDANCE_NEP_ISA,
    contenu_referentiel,
    normes_audit,
)
from app.models.cabinet import Cabinet
from app.models.client import Client
from app.models.mission import Mission


def test_contenu_par_referentiel():
    assert contenu_referentiel("PCG_FR")["zone"] == "France"
    assert "SYSCOHADA" in contenu_referentiel("SYSCOHADA_OHADA")["libelle"]
    assert contenu_referentiel("INCONNU") is None
    # normes d'audit : ISA pour l'international, repli NEP sinon
    assert normes_audit("IFRS") == ["ISA — International Standards on Auditing (IAASB)"]
    assert "NEP" in normes_audit("INCONNU")[0]


def test_correspondance_nep_isa():
    paires = {(nep, isa) for _, nep, isa in CORRESPONDANCE_NEP_ISA}
    assert ("NEP 520", "ISA 520") in paires
    assert ("NEP 700", "ISA 700") in paires


def _ck(client):
    return client.post("/login", data={"email": "admin@axiome.io", "password": "Test!2026"},
                       follow_redirects=False).cookies


def test_page_referentiels(client):
    r = client.get("/vue/referentiels", cookies=_ck(client))
    assert r.status_code == 200
    assert "SYSCOHADA révisé" in r.text and "NEP 520" in r.text and "ISA 520" in r.text


def test_normes_affichees_selon_mission(client, db_session):
    cab = db_session.query(Cabinet).first()
    if cab is None:
        cab = Cabinet(nom="Cab"); db_session.add(cab); db_session.flush()
    cl = Client(cabinet_id=cab.id, raison_sociale="Baobab SA"); db_session.add(cl); db_session.flush()
    m = Mission(client_id=cl.id, intitule="Audit Baobab", referentiel="SYSCOHADA_OHADA",
                pays="Sénégal", devise="XOF"); db_session.add(m); db_session.commit()
    r = client.get(f"/missions/{m.id}/vue", cookies=_ck(client))
    assert "ISA" in r.text and "Acte uniforme OHADA" in r.text
