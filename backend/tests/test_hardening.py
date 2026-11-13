"""Phase 9 — durcissement : sondes, en-têtes de sécurité, garde-fous de config."""
from __future__ import annotations

import pytest

from app.core.config import Settings, verifier_configuration


def test_readyz_ok(client):
    r = client.get("/readyz")
    assert r.status_code == 200 and r.json()["status"] == "ready"


def test_security_headers(client):
    r = client.get("/healthz")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert r.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


def test_config_prod_valide_ne_leve_pas():
    s = Settings(_env_file=None, environment="production", secret_key="k" * 64,
                 admin_password="MotDePasseFort!2026", superadmin_password="EditeurFort!2026xyz",
                 database_url="postgresql+psycopg2://u:p@db:5432/axiome",
                 payment_sandbox=False)  # le paiement de test est interdit en production
    verifier_configuration(s)  # ne doit pas lever


def test_config_prod_refuse_paiement_de_test():
    s = Settings(_env_file=None, environment="production", secret_key="k" * 64, admin_password="MotDePasseFort!2026", superadmin_password="EditeurFort!2026xyz",
                 database_url="postgresql+psycopg2://u:p@db:5432/axiome", payment_sandbox=True)
    with pytest.raises(RuntimeError, match="PAYMENT_SANDBOX"):
        verifier_configuration(s)


def test_config_prod_refuse_valeurs_par_defaut():
    s = Settings(_env_file=None, environment="production")  # secret/admin/sqlite par défaut
    with pytest.raises(RuntimeError) as exc:
        verifier_configuration(s)
    msg = str(exc.value)
    assert "SECRET_KEY" in msg and "ADMIN_PASSWORD" in msg and "SQLite" in msg


def test_config_dev_permissif():
    verifier_configuration(Settings(_env_file=None, environment="development"))  # rien en dev
