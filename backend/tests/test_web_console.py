"""Deux espaces : console éditeur (SUPERADMIN) + gestion collaborateurs (CAC) + cloisonnement."""
from __future__ import annotations

from _helpers_ecrans import ck

from app.core.security import hash_password
from app.models.cabinet import Cabinet
from app.models.client import Client
from app.models.mission import Mission
from app.models.user import Role, User


def _mk_superadmin(db):
    role = db.query(Role).filter_by(code="SUPERADMIN").first()
    u = User(email="editeur@test.io", hashed_password=hash_password("Editeur!2026"),
             nom_complet="Éditeur", is_active=True)
    u.roles.append(role)
    db.add(u); db.commit()
    return u


def _login(client, email, pwd):
    return client.post("/login", data={"email": email, "password": pwd},
                       follow_redirects=False)


def test_editeur_routage_et_console(client, db_session):
    _mk_superadmin(db_session)
    r = _login(client, "editeur@test.io", "Editeur!2026")
    assert r.status_code == 302 and r.headers["location"] == "/console"
    page = client.get("/console", cookies=r.cookies)
    assert page.status_code == 200 and "Tous les cabinets" in page.text


def test_admin_cabinet_refuse_console(client):
    r = client.get("/console", cookies=ck(client))
    assert r.status_code == 403


def test_editeur_cree_cabinet_avec_cac(client, db_session):
    _mk_superadmin(db_session)
    cke = _login(client, "editeur@test.io", "Editeur!2026").cookies
    client.post("/console/cabinet", cookies=cke, follow_redirects=False, data={
        "nom": "Cabinet Delta", "pays": "France", "referentiel_defaut": "PCG_FR",
        "devise_defaut": "EUR", "cac_email": "cac@delta.fr", "cac_nom": "CAC Delta",
        "cac_password": "MotDePasse!2026"})
    cab = db_session.query(Cabinet).filter_by(nom="Cabinet Delta").first()
    assert cab is not None
    cac = db_session.query(User).filter_by(email="cac@delta.fr").first()
    assert cac is not None and cac.cabinet_id == cab.id and cac.has_role("ADMIN")


def test_editeur_suspend_cabinet_bloque_login(client, db_session):
    _mk_superadmin(db_session)
    cab = Cabinet(nom="Cabinet Suspendu"); db_session.add(cab); db_session.flush()
    admin_role = db_session.query(Role).filter_by(code="ADMIN").first()
    u = User(email="cac@susp.fr", hashed_password=hash_password("Pass!2026"),
             nom_complet="CAC", is_active=True, cabinet_id=cab.id)
    u.roles.append(admin_role); db_session.add(u); db_session.commit()
    # Avant suspension : login OK.
    assert _login(client, "cac@susp.fr", "Pass!2026").status_code == 302
    # L'éditeur suspend le cabinet.
    cke = _login(client, "editeur@test.io", "Editeur!2026").cookies
    client.post(f"/console/cabinet/{cab.id}/toggle", cookies=cke, follow_redirects=False)
    db_session.refresh(cab)
    assert cab.is_archived is True
    # Après suspension : login bloqué (403).
    r = _login(client, "cac@susp.fr", "Pass!2026")
    assert r.status_code == 403 and "suspendu" in r.text.lower()


def test_cac_cree_collaborateur_et_refuse_superadmin(client, db_session):
    # Le CAC de test (admin@axiome.io) crée un auditeur.
    client.post("/vue/administration/collaborateur", cookies=ck(client), follow_redirects=False,
                data={"email": "audit@test.io", "nom_complet": "Nouvel Auditeur",
                      "role": "AUDITEUR", "password": "MotDePasse!2026"})
    u = db_session.query(User).filter_by(email="audit@test.io").first()
    cab = db_session.query(Cabinet).first()
    assert u is not None and u.cabinet_id == cab.id and u.has_role("AUDITEUR")
    # Le CAC ne peut PAS créer un SUPERADMIN.
    r = client.post("/vue/administration/collaborateur", cookies=ck(client), follow_redirects=False,
                    data={"email": "pirate@test.io", "role": "SUPERADMIN",
                          "password": "MotDePasse!2026"})
    assert r.status_code == 403
    assert db_session.query(User).filter_by(email="pirate@test.io").first() is None


def test_cloisonnement_missions_entre_cabinets(client, db_session):
    # Mission dans un AUTRE cabinet que celui de l'admin de test.
    autre = Cabinet(nom="Autre Cabinet"); db_session.add(autre); db_session.flush()
    cli = Client(cabinet_id=autre.id, raison_sociale="Bravo SAS"); db_session.add(cli); db_session.flush()
    m = Mission(client_id=cli.id, intitule="Audit Bravo", referentiel="PCG_FR",
                pays="France", devise="EUR", exercice="2025")
    db_session.add(m); db_session.commit()
    # L'admin (cabinet Test) ne voit pas / n'accède pas à cette mission.
    liste = client.get("/missions", cookies=ck(client))
    assert "Audit Bravo" not in liste.text
    detail = client.get(f"/missions/{m.id}/vue", cookies=ck(client))
    assert detail.status_code == 403
    # L'éditeur (SUPERADMIN) y accède.
    _mk_superadmin(db_session)
    cke = _login(client, "editeur@test.io", "Editeur!2026").cookies
    assert client.get(f"/missions/{m.id}/vue", cookies=cke).status_code == 200
