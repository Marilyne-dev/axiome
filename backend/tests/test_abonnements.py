"""Abonnement SaaS : offres, inscription, paiement, activation, verrouillage de l'espace."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.models.billing import Abonnement, Paiement
from app.models.cabinet import Cabinet
from app.services import billing_service, payment_providers

SIGNUP = {"plan_code": "cabinet", "periode": "mensuel", "devise": "EUR", "cabinet_nom": "Cabinet Nouveau",
          "pays": "France", "admin_nom": "Marie Dupont", "admin_email": "marie@nouveau.fr", "admin_password": "MotDePasse2026"}


@pytest.fixture()
def avec_plans(db_session):
    billing_service.seed_plans(db_session); db_session.commit()
    return db_session


def _login(client, email="marie@nouveau.fr", pwd="MotDePasse2026"):
    return {"Authorization": "Bearer " + client.post("/auth/login", json={"email": email, "password": pwd}).json()["access_token"]}


def test_offres_publiques(client, avec_plans):
    r = client.get("/public/plans").json()
    assert [p["code"] for p in r] == ["essentiel", "cabinet", "reseau"]
    assert r[1]["featured"] and r[1]["prix"]["EUR"]["mensuel"] == 14900 and r[1]["prix"]["XOF"]["annuel"] == 980000


def test_inscription_cree_espace_en_attente_de_paiement(client, avec_plans):
    r = client.post("/public/signup", json=SIGNUP)
    assert r.status_code == 201
    j = r.json()
    assert j["montant"] == 14900 and j["devise"] == "EUR" and j["checkout_url"].endswith("/paiement/" + j["reference"])
    cab = avec_plans.query(Cabinet).filter_by(nom="Cabinet Nouveau").one()
    assert (cab.quota_collaborateurs, cab.quota_missions) == (10, 30)
    # espace verrouillé tant que non payé
    h = _login(client)
    d = client.get("/espace/dashboard", headers=h).json()
    assert d["verrouille"] is True and d["abonnement"]["statut"] == "en_attente_paiement" and d["missions"] == []
    assert client.get("/espace/clients", headers=h).status_code == 402
    assert client.get("/espace/missions", headers=h).status_code == 402


def test_paiement_test_active_l_espace(client, avec_plans):
    ref = client.post("/public/signup", json=SIGNUP).json()["reference"]
    assert client.get(f"/public/paiements/{ref}").json()["statut"] == "en_attente"
    assert client.post(f"/public/paiements/{ref}/confirmer-test").json()["statut"] == "paye"
    etat = client.get(f"/public/paiements/{ref}").json()
    assert etat["statut"] == "paye" and etat["abonnement"] == "actif"
    h = _login(client)
    assert client.get("/espace/dashboard", headers=h).json()["verrouille"] is False
    assert client.get("/espace/clients", headers=h).status_code == 200
    abo = avec_plans.query(Abonnement).one()
    assert abo.date_fin - abo.date_debut >= timedelta(days=29)


def test_activation_idempotente_et_prolongation(client, avec_plans):
    ref = client.post("/public/signup", json=SIGNUP).json()["reference"]
    client.post(f"/public/paiements/{ref}/confirmer-test")
    abo = avec_plans.query(Abonnement).one(); fin1 = abo.date_fin
    pay = avec_plans.query(Paiement).filter_by(reference=ref).one()
    billing_service.activer(avec_plans, pay)                       # rejouer ne prolonge pas
    avec_plans.refresh(abo); assert abo.date_fin == fin1
    h = _login(client)
    nouveau = client.post("/espace/abonnement/payer", headers=h).json()["reference"]
    client.post(f"/public/paiements/{nouveau}/confirmer-test")      # renouvellement : s'ajoute à l'échéance
    avec_plans.refresh(abo)
    assert billing_service._aware(abo.date_fin) >= billing_service._aware(fin1) + timedelta(days=29)


def test_abonnement_expire_verrouille(client, avec_plans):
    ref = client.post("/public/signup", json=SIGNUP).json()["reference"]
    client.post(f"/public/paiements/{ref}/confirmer-test")
    abo = avec_plans.query(Abonnement).one(); abo.date_fin = datetime.now(timezone.utc) - timedelta(days=1); avec_plans.commit()
    h = _login(client)
    assert client.get("/espace/clients", headers=h).status_code == 402
    assert client.get("/espace/abonnement", headers=h).json()["abonnement"]["statut"] == "expire"


def test_validations_inscription(client, avec_plans):
    assert client.post("/public/signup", json={**SIGNUP, "plan_code": "inconnu"}).status_code == 404
    assert client.post("/public/signup", json={**SIGNUP, "admin_password": "court1"}).status_code == 422
    assert client.post("/public/signup", json={**SIGNUP, "admin_password": "uniquementlettres"}).status_code == 422
    assert client.post("/public/signup", json={**SIGNUP, "devise": "USD"}).status_code == 422
    assert client.post("/public/signup", json={**SIGNUP, "admin_email": "pas-un-email"}).status_code == 422
    client.post("/public/signup", json=SIGNUP)
    assert client.post("/public/signup", json=SIGNUP).status_code == 409        # e-mail déjà utilisé


def test_xof_zone_ohada_et_fournisseur(client, avec_plans):
    j = client.post("/public/signup", json={**SIGNUP, "devise": "XOF", "periode": "annuel", "admin_email": "k@abidjan.ci"}).json()
    assert j["montant"] == 980000 and j["devise"] == "XOF"
    assert avec_plans.query(Cabinet).filter_by(nom="Cabinet Nouveau").one().referentiel_defaut == "SYSCOHADA_OHADA"


def test_methodes_selon_devise_et_configuration(monkeypatch):
    st = payment_providers.settings
    for k in ("stripe_secret_key", "stripe_publishable_key", "fedapay_secret_key", "virement_iban", "virement_titulaire"):
        monkeypatch.setattr(st, k, "")
    assert payment_providers.methodes_disponibles("EUR") == [] and payment_providers.methodes_disponibles("XOF") == []
    monkeypatch.setattr(st, "stripe_secret_key", "sk_test_x"); monkeypatch.setattr(st, "stripe_publishable_key", "pk_test_x")
    monkeypatch.setattr(st, "fedapay_secret_key", "sk_sandbox_x")
    monkeypatch.setattr(st, "virement_iban", "FR7600000000"); monkeypatch.setattr(st, "virement_titulaire", "AXIOME")
    assert [m["code"] for m in payment_providers.methodes_disponibles("EUR")] == ["stripe", "virement"]
    assert [m["code"] for m in payment_providers.methodes_disponibles("XOF")] == ["mobile_money", "fedapay", "virement"]


def test_virement_puis_confirmation_editeur(client, avec_plans, monkeypatch):
    st = payment_providers.settings
    monkeypatch.setattr(st, "virement_iban", "FR7600000000"); monkeypatch.setattr(st, "virement_titulaire", "AXIOME")
    ref = client.post("/public/signup", json=SIGNUP).json()["reference"]
    coord = client.post(f"/public/paiements/{ref}/virement").json()
    assert coord["iban"] == "FR7600000000" and coord["reference"].startswith("AXIOME-") and coord["montant"] == 14900
    assert client.get(f"/public/paiements/{ref}").json()["statut"] == "en_attente"      # jamais actif sans confirmation
    assert client.post(f"/admin/paiements/{ref}/confirmer-virement", headers=_login(client)).status_code == 403
    assert client.post(f"/admin/paiements/{ref}/confirmer-virement").status_code in (401, 403)


def test_mobile_money_envoie_la_demande(client, avec_plans, monkeypatch):
    st = payment_providers.settings
    monkeypatch.setattr(st, "fedapay_secret_key", "sk_sandbox_x")
    vu = {}
    monkeypatch.setattr(payment_providers, "fedapay_mobile_money", lambda **kw: vu.update(kw) or "tx_42")
    ref = client.post("/public/signup", json={**SIGNUP, "devise": "XOF", "admin_email": "k@cotonou.bj"}).json()["reference"]
    r = client.post(f"/public/paiements/{ref}/mobile-money", json={"operateur": "mtn", "numero": "97 80 80 80"})
    assert r.status_code == 200 and vu["operateur"] == "mtn" and vu["montant"] == 98000
    pay = avec_plans.query(Paiement).filter_by(reference=ref).one()
    assert (pay.fournisseur, pay.fournisseur_ref, pay.statut) == ("fedapay", "tx_42", "en_attente")
    assert client.post(f"/public/paiements/{ref}/stripe").status_code == 422          # Stripe refusé en XOF


def test_stripe_cree_une_intention(client, avec_plans, monkeypatch):
    st = payment_providers.settings
    monkeypatch.setattr(st, "stripe_publishable_key", "pk_test_x")
    monkeypatch.setattr(payment_providers, "stripe_creer_intention", lambda **kw: ("pi_1", "pi_1_secret"))
    ref = client.post("/public/signup", json=SIGNUP).json()["reference"]
    j = client.post(f"/public/paiements/{ref}/stripe").json()
    assert j == {"client_secret": "pi_1_secret", "cle_publique": "pk_test_x"}
    monkeypatch.setattr(payment_providers, "verifier", lambda f, r: "paye")
    assert client.get(f"/public/paiements/{ref}").json()["abonnement"] == "actif"


def test_operateur_inconnu_refuse():
    with pytest.raises(payment_providers.ErreurPaiement):
        payment_providers.fedapay_mobile_money(reference="r", montant=1, devise="XOF", libelle="x", email="a@b.c",
                                               nom="A B", operateur="inconnu", numero="97808080")


def test_test_interdit_en_production(client, avec_plans, monkeypatch):
    ref = client.post("/public/signup", json=SIGNUP).json()["reference"]
    monkeypatch.setattr("app.api.routes_public.settings.payment_sandbox", False)
    assert client.post(f"/public/paiements/{ref}/confirmer-test").status_code == 403
    assert client.get(f"/public/paiements/{ref}").json()["statut"] == "en_attente"


def test_webhook_ne_croit_pas_la_notification(client, avec_plans, monkeypatch):
    """Une fausse notification « payé » n'active rien : l'état est relu chez le fournisseur."""
    ref = client.post("/public/signup", json=SIGNUP).json()["reference"]
    pay = avec_plans.query(Paiement).filter_by(reference=ref).one()
    pay.fournisseur, pay.fournisseur_ref = "stripe", "cs_test_123"; avec_plans.commit()
    monkeypatch.setattr(payment_providers, "verifier", lambda f, r: "en_attente")
    r = client.post("/webhooks/stripe", json={"type": "checkout.session.completed", "data": {"object": {"id": "cs_test_123", "payment_status": "paid"}}})
    assert r.status_code == 200
    avec_plans.refresh(pay); assert pay.statut == "en_attente"
    monkeypatch.setattr(payment_providers, "verifier", lambda f, r: "paye")      # le fournisseur confirme réellement
    client.post("/webhooks/stripe", json={"data": {"object": {"id": "cs_test_123"}}})
    avec_plans.refresh(pay); assert pay.statut == "paye"


def test_cabinet_sans_abonnement_reste_actif(client, db_session):
    h = _login(client, "admin@axiome.io", "Test!2026")
    assert client.get("/espace/clients", headers=h).status_code == 200


def test_seed_plans_idempotent(db_session):
    billing_service.seed_plans(db_session); billing_service.seed_plans(db_session); db_session.commit()
    assert len(billing_service.liste_plans(db_session)) == 3
