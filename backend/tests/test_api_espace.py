"""API de l'espace cabinet : cloisonnement strict par cabinet (SaaS multi-entreprises)."""
from __future__ import annotations

from app.core.security import hash_password
from app.models.cabinet import Cabinet
from app.models.client import Client
from app.models.mission import Mission
from app.models.user import Role, User


def _login(client, email, pwd):
    return {"Authorization": "Bearer " + client.post("/auth/login", json={"email": email, "password": pwd}).json()["access_token"]}


def _cabinet_avec_donnees(db, nom, client_nom):
    cab = Cabinet(nom=nom, quota_collaborateurs=3, quota_missions=10); db.add(cab); db.flush()
    cli = Client(cabinet_id=cab.id, raison_sociale=client_nom, pays="France"); db.add(cli); db.flush()
    db.add(Mission(client_id=cli.id, intitule=f"Mission {client_nom}", exercice="2025", referentiel="PCG_FR"))
    db.commit()
    return cab


def _user(db, email, role, cabinet_id=None):
    u = User(email=email, hashed_password=hash_password("Test!2026"), nom_complet=email, is_active=True, cabinet_id=cabinet_id)
    u.roles.append(db.query(Role).filter_by(code=role).first()); db.add(u); db.commit()


def test_non_authentifie_refuse(client):
    for path in ("/espace/dashboard", "/espace/clients", "/espace/missions"):
        assert client.get(path).status_code == 401


def test_cabinet_ne_voit_que_ses_donnees(client, db_session):
    cab_a = db_session.query(Cabinet).first()           # cabinet de admin@axiome.io
    db_session.add(Client(cabinet_id=cab_a.id, raison_sociale="Client A")); db_session.commit()
    _cabinet_avec_donnees(db_session, "Cabinet B", "Client Secret B")
    h = _login(client, "admin@axiome.io", "Test!2026")
    noms = [c["raison_sociale"] for c in client.get("/espace/clients", headers=h).json()]
    assert noms == ["Client A"]
    dash = client.get("/espace/dashboard", headers=h).json()
    assert dash["kpis"]["clients"] == 1 and dash["kpis"]["missions"] == 0
    assert "Client Secret B" not in str(dash) and client.get("/espace/missions", headers=h).json() == []


def test_dashboard_missions_et_quotas(client, db_session):
    cab = _cabinet_avec_donnees(db_session, "Cabinet C", "Gamma")
    _user(db_session, "chef@c.fr", "ADMIN", cab.id)
    d = client.get("/espace/dashboard", headers=_login(client, "chef@c.fr", "Test!2026")).json()
    assert d["cabinet"]["nom"] == "Cabinet C"
    assert d["cabinet"]["collaborateurs"] == {"utilises": 1, "quota": 3}
    assert d["cabinet"]["missions"] == {"utilises": 1, "quota": 10}
    assert d["kpis"]["clients"] == 1 and d["missions"][0]["client"] == "Gamma"


def test_utilisateur_sans_cabinet_ne_voit_rien(client, db_session):
    _cabinet_avec_donnees(db_session, "Cabinet D", "Delta")
    _user(db_session, "libre@x.fr", "ADMIN", None)
    h = _login(client, "libre@x.fr", "Test!2026")
    d = client.get("/espace/dashboard", headers=h).json()
    assert d["cabinet"] is None and d["missions"] == [] and d["kpis"]["clients"] == 0
    assert client.get("/espace/clients", headers=h).json() == []


def test_portail_client_exclu(client, db_session):
    cab = _cabinet_avec_donnees(db_session, "Cabinet E", "Epsilon")
    _user(db_session, "entite@e.fr", "CLIENT", cab.id)
    assert client.get("/espace/dashboard", headers=_login(client, "entite@e.fr", "Test!2026")).status_code == 403


def test_pilotage_jinja_cloisonne(client, db_session):
    _cabinet_avec_donnees(db_session, "Cabinet F", "Zeta Confidentiel")
    h = _login(client, "admin@axiome.io", "Test!2026")
    page = client.get("/vue/pilotage", headers=h)
    assert page.status_code == 200 and "Zeta Confidentiel" not in page.text
