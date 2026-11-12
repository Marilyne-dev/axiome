"""Phase 6 — portail client : cloisonnement, redirection, dépôt de pièces."""
from __future__ import annotations

from app.core.security import hash_password
from app.models.audit import Document
from app.models.cabinet import Cabinet
from app.models.client import Client
from app.models.mission import Mission
from app.models.user import Role, User


def _setup(db):
    cab = Cabinet(nom="Cab"); db.add(cab); db.flush()
    alpha = Client(cabinet_id=cab.id, raison_sociale="Alpha")
    baobab = Client(cabinet_id=cab.id, raison_sociale="Baobab")
    db.add_all([alpha, baobab]); db.flush()
    m_a = Mission(client_id=alpha.id, intitule="Audit Alpha", referentiel="PCG_FR",
                  pays="France", devise="EUR")
    m_b = Mission(client_id=baobab.id, intitule="Audit Baobab", referentiel="PCG_FR",
                  pays="France", devise="EUR")
    db.add_all([m_a, m_b]); db.flush()
    role = db.query(Role).filter_by(code="CLIENT").first() or Role(code="CLIENT", libelle="Client")
    db.add(role); db.flush()
    u = User(email="c@portail.io", hashed_password=hash_password("Pwd!2026"),
             is_active=True, lang="fr", client_id=alpha.id)
    u.roles.append(role)
    db.add(u); db.commit()
    return m_a.id, m_b.id


def _login(client):
    return client.post("/login", data={"email": "c@portail.io", "password": "Pwd!2026"},
                       follow_redirects=False)


def test_connexion_client_redirige_vers_portail(client, db_session):
    _setup(db_session)
    assert _login(client).headers["location"] == "/portail"


def test_cloisonnement_portail(client, db_session):
    ma, mb = _setup(db_session)
    ck = _login(client).cookies
    assert client.get("/portail", cookies=ck).status_code == 200
    assert client.get(f"/portail/missions/{ma}", cookies=ck).status_code == 200
    # dossier d'un AUTRE client -> interdit
    assert client.get(f"/portail/missions/{mb}", cookies=ck).status_code == 403


def test_depot_piece_portail(client, db_session):
    ma, _ = _setup(db_session)
    ck = _login(client).cookies
    client.post(f"/portail/missions/{ma}/documents/upload", cookies=ck,
                files={"fichier": ("piece.pdf", b"%PDF-1.4", "application/pdf")},
                follow_redirects=False)
    doc = db_session.query(Document).filter_by(mission_id=ma).first()
    assert doc is not None and doc.cycle_code == "PORTAIL"
