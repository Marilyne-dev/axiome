"""Changement d'offre, règle de quota (administrateur non décompté), console éditeur : offres et abonnements."""
from __future__ import annotations

from datetime import timedelta

import pytest

from app.core.security import hash_password
from app.models.billing import Abonnement, Paiement, Plan
from app.models.cabinet import Cabinet
from app.models.user import Role, User
from app.services import billing_service

SIGNUP = {"plan_code": "essentiel", "periode": "mensuel", "devise": "EUR", "cabinet_nom": "Cabinet Evolution",
          "pays": "France", "admin_nom": "Marie Dupont", "admin_email": "marie@evolution.fr",
          "admin_password": "MotDePasse2026"}


@pytest.fixture()
def db(db_session):
    billing_service.seed_plans(db_session); db_session.commit()
    return db_session


def _h(client, email="marie@evolution.fr", pwd="MotDePasse2026"):
    tok = client.post("/auth/login", json={"email": email, "password": pwd}).json()["access_token"]
    return {"Authorization": "Bearer " + tok}


def _abonne(client, **over):
    """Cabinet abonné et payé (mode test)."""
    ref = client.post("/public/signup", json={**SIGNUP, **over}).json()["reference"]
    client.post(f"/public/paiements/{ref}/confirmer-test")
    return _h(client, over.get("admin_email", SIGNUP["admin_email"]))


def _collab(db, cab, n):
    for i in range(n):
        u = User(email=f"c{i}@evolution.fr", hashed_password="x", nom_complet=f"C{i}", is_active=True, cabinet_id=cab.id)
        u.roles.append(db.query(Role).filter_by(code="AUDITEUR").first() or db.query(Role).first())
        db.add(u)
    db.commit()


# ------------------------------------------------------------------ quota : l'administrateur n'est pas décompté
def test_administrateur_non_decompte_du_quota(client, db):
    h = _abonne(client)
    cab = db.query(Cabinet).filter_by(nom="Cabinet Evolution").one()
    assert billing_service.compter_collaborateurs(db, cab.id) == 0           # l'admin seul = 0 collaborateur
    d = client.get("/espace/dashboard", headers=h).json()["cabinet"]["collaborateurs"]
    assert d == {"utilises": 0, "quota": 2}
    _collab(db, cab, 2)
    assert billing_service.compter_collaborateurs(db, cab.id) == 2           # administrateur + 2 collaborateurs : plein
    assert client.get("/espace/dashboard", headers=h).json()["cabinet"]["collaborateurs"]["utilises"] == 2


# ------------------------------------------------------------------ changement d'offre
def test_montee_en_gamme_apres_paiement(client, db):
    h = _abonne(client)
    abo = db.query(Abonnement).one()
    fin_initiale = abo.date_fin
    offres = client.get("/espace/offres", headers=h).json()
    assert offres["peut_changer"] is True
    assert [o["code"] for o in offres["offres"]] == ["essentiel", "cabinet", "reseau"]
    assert next(o for o in offres["offres"] if o["code"] == "essentiel")["actuelle"] is True

    r = client.post("/espace/abonnement/changer-offre", headers=h, json={"plan_code": "cabinet", "periode": "annuel"})
    assert r.status_code == 200 and r.json()["montant"] == 149000 and r.json()["devise"] == "EUR"
    ref = r.json()["reference"]
    db.refresh(abo)
    assert db.get(Plan, abo.plan_id).code == "essentiel"                      # rien ne change avant le paiement
    assert client.get(f"/public/paiements/{ref}").json()["plan"] == "Cabinet"  # la page de paiement montre l'offre visée

    assert client.post(f"/public/paiements/{ref}/confirmer-test").json()["statut"] == "paye"
    db.refresh(abo)
    assert db.get(Plan, abo.plan_id).code == "cabinet" and abo.periode == "annuel"
    cab = db.get(Cabinet, abo.cabinet_id)
    assert (cab.quota_collaborateurs, cab.quota_missions) == (10, 30)
    assert billing_service._aware(abo.date_fin) - billing_service._aware(abo.date_debut) >= timedelta(days=364) or \
        billing_service._aware(abo.date_fin) > billing_service._aware(fin_initiale) + timedelta(days=300)
    info = client.get("/espace/abonnement", headers=h).json()
    assert info["abonnement"]["plan"] == "Cabinet" and info["abonnement"]["plan_code"] == "cabinet"


def test_rejouer_paiement_ne_change_rien(client, db):
    h = _abonne(client)
    ref = client.post("/espace/abonnement/changer-offre", headers=h, json={"plan_code": "cabinet", "periode": "mensuel"}).json()["reference"]
    client.post(f"/public/paiements/{ref}/confirmer-test")
    abo = db.query(Abonnement).one(); fin = abo.date_fin
    billing_service.activer(db, db.query(Paiement).filter_by(reference=ref).one())
    db.refresh(abo); assert abo.date_fin == fin


def test_descente_refusee_si_usage_depasse_les_quotas(client, db):
    h = _abonne(client, plan_code="cabinet")
    cab = db.query(Cabinet).filter_by(nom="Cabinet Evolution").one()
    _collab(db, cab, 3)                                                       # 3 > 2 autorisés par « Essentiel »
    r = client.post("/espace/abonnement/changer-offre", headers=h, json={"plan_code": "essentiel", "periode": "mensuel"})
    assert r.status_code == 409 and "collaborateurs" in r.json()["detail"]
    o = {x["code"]: x for x in client.get("/espace/offres", headers=h).json()["offres"]}
    assert o["essentiel"]["possible"] is False and o["reseau"]["possible"] is True


def test_memes_offre_et_periode_refusees(client, db):
    h = _abonne(client)
    r = client.post("/espace/abonnement/changer-offre", headers=h, json={"plan_code": "essentiel", "periode": "mensuel"})
    assert r.status_code == 409
    assert client.post("/espace/abonnement/changer-offre", headers=h, json={"plan_code": "inconnue", "periode": "mensuel"}).status_code == 404
    assert client.post("/espace/abonnement/changer-offre", headers=h, json={"plan_code": "cabinet", "periode": "hebdo"}).status_code == 422


def test_changement_reserve_a_l_administrateur(client, db):
    _abonne(client)
    cab = db.query(Cabinet).filter_by(nom="Cabinet Evolution").one()
    u = User(email="aud@evolution.fr", hashed_password=hash_password("Auditeur2026!"), nom_complet="Aud", is_active=True, cabinet_id=cab.id)
    u.roles.append(db.query(Role).filter_by(code="AUDITEUR").one()); db.add(u); db.commit()
    h = _h(client, "aud@evolution.fr", "Auditeur2026!")
    assert client.post("/espace/abonnement/changer-offre", headers=h, json={"plan_code": "cabinet", "periode": "mensuel"}).status_code == 403
    assert client.get("/espace/offres", headers=h).json()["peut_changer"] is False


def test_changement_avant_premier_paiement_remplace_le_choix(client, db):
    ref0 = client.post("/public/signup", json=SIGNUP).json()["reference"]    # jamais payé
    h = _h(client)
    r = client.post("/espace/abonnement/changer-offre", headers=h, json={"plan_code": "reseau", "periode": "mensuel"}).json()
    assert r["montant"] == 39900
    assert db.query(Paiement).filter_by(reference=ref0).one().statut == "echoue"   # l'ancien paiement est clos
    client.post(f"/public/paiements/{r['reference']}/confirmer-test")
    abo = db.query(Abonnement).one()
    assert db.get(Plan, abo.plan_id).code == "reseau" and abo.statut == "actif"
    cab = db.get(Cabinet, abo.cabinet_id)
    assert (cab.quota_collaborateurs, cab.quota_missions) == (0, 0)


# ------------------------------------------------------------------ console éditeur
def _editeur(client, db):
    u = User(email="editeur@axiome.io", hashed_password=hash_password("Editeur!2026"), nom_complet="Éditeur", is_active=True)
    u.roles.append(db.query(Role).filter_by(code="SUPERADMIN").one()); db.add(u); db.commit()
    return client.post("/login", data={"email": "editeur@axiome.io", "password": "Editeur!2026"}, follow_redirects=False).cookies


def test_console_reservee_a_l_editeur(client, db):
    from _helpers_ecrans import ck
    assert client.get("/console/offres", cookies=ck(client)).status_code == 403
    assert client.get("/console/abonnements", cookies=ck(client)).status_code == 403
    client.cookies.clear()
    assert client.get("/console/offres", follow_redirects=False).status_code == 302


def test_console_modifie_les_prix_et_les_quotas(client, db):
    c = _editeur(client, db)
    page = client.get("/console/offres", cookies=c)
    assert page.status_code == 200 and "Essentiel" in page.text and "Cabinet" in page.text
    plan = db.query(Plan).filter_by(code="essentiel").one()
    r = client.post(f"/console/offres/{plan.id}", cookies=c, follow_redirects=False, data={
        "nom": "Essentiel", "description": "Petit cabinet", "fonctionnalites": "Ligne A\nLigne B",
        "prix_mensuel_eur": "59,50", "prix_annuel_eur": "590", "prix_mensuel_xof": "40000", "prix_annuel_xof": "400000",
        "quota_collaborateurs": "3", "quota_missions": "8", "ordre": "1", "is_active": "on"})
    assert r.status_code == 302 and "err=" not in r.headers["location"]
    db.refresh(plan)
    assert (plan.prix_mensuel_eur, plan.prix_annuel_eur, plan.quota_collaborateurs, plan.quota_missions) == (5950, 59000, 3, 8)
    pub = client.get("/public/plans").json()
    assert pub[0]["prix"]["EUR"]["mensuel"] == 5950 and pub[0]["fonctionnalites"] == ["Ligne A", "Ligne B"]


def test_console_prix_invalide_rejete(client, db):
    c = _editeur(client, db)
    plan = db.query(Plan).filter_by(code="essentiel").one()
    r = client.post(f"/console/offres/{plan.id}", cookies=c, follow_redirects=False, data={
        "nom": "Essentiel", "prix_mensuel_eur": "abc", "quota_collaborateurs": "2", "quota_missions": "5", "ordre": "1", "is_active": "on"})
    assert "err=" in r.headers["location"]
    db.refresh(plan); assert plan.prix_mensuel_eur == 4900


def test_console_applique_les_quotas_aux_cabinets_existants(client, db):
    _abonne(client)
    c = _editeur(client, db)
    plan = db.query(Plan).filter_by(code="essentiel").one()
    client.post(f"/console/offres/{plan.id}", cookies=c, follow_redirects=False, data={
        "nom": "Essentiel", "prix_mensuel_eur": "49", "prix_annuel_eur": "490", "prix_mensuel_xof": "32000", "prix_annuel_xof": "320000",
        "quota_collaborateurs": "4", "quota_missions": "9", "ordre": "1", "is_active": "on", "appliquer_aux_cabinets": "on"})
    cab = db.query(Cabinet).filter_by(nom="Cabinet Evolution").one()
    assert (cab.quota_collaborateurs, cab.quota_missions) == (4, 9)


def test_console_cree_une_offre(client, db):
    c = _editeur(client, db)
    r = client.post("/console/offres", cookies=c, follow_redirects=False, data={
        "code": "premium", "nom": "Premium", "prix_mensuel_eur": "99", "prix_annuel_eur": "990", "prix_mensuel_xof": "65000",
        "prix_annuel_xof": "650000", "quota_collaborateurs": "20", "quota_missions": "0", "ordre": "4", "is_active": "on"})
    assert "err=" not in r.headers["location"]
    assert db.query(Plan).filter_by(code="premium").one().prix_mensuel_eur == 9900
    dup = client.post("/console/offres", cookies=c, follow_redirects=False, data={"code": "premium", "nom": "Autre"})
    assert "err=" in dup.headers["location"]


def test_console_suivi_abonnements_et_virement(client, db, monkeypatch):
    from app.services import payment_providers
    monkeypatch.setattr(payment_providers.settings, "virement_iban", "FR7630001007941234567890185")
    monkeypatch.setattr(payment_providers.settings, "virement_titulaire", "AXIOME SAS")
    ref = client.post("/public/signup", json={**SIGNUP, "admin_email": "v@evolution.fr"}).json()["reference"]
    assert client.post(f"/public/paiements/{ref}/virement").status_code == 200
    c = _editeur(client, db)
    page = client.get("/console/abonnements", cookies=c)
    assert page.status_code == 200 and "Cabinet Evolution" in page.text and "Confirmer le virement reçu" in page.text
    assert "En attente de paiement" in page.text
    client.post(f"/console/paiements/{ref}/confirmer-virement", cookies=c, follow_redirects=False)
    assert db.query(Paiement).filter_by(reference=ref).one().statut == "paye"
    page2 = client.get("/console/abonnements?statut=actif", cookies=c)
    assert "Cabinet Evolution" in page2.text and "Confirmer le virement reçu" not in page2.text
