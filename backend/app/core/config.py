"""Configuration centralisée d'AXIOME.

Charge les paramètres depuis l'environnement (.env) via pydantic-settings.
Aucun secret n'est écrit en dur : tout provient de variables d'environnement.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Paramètres applicatifs, typés et validés au démarrage."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Application
    app_name: str = "AXIOME Audit"
    environment: str = "development"
    base_url: str = "http://localhost:8000"

    # Localisation par défaut
    default_lang: str = "fr"
    default_country: str = "France"
    default_currency: str = "EUR"
    default_referentiel: str = "PCG_FR"

    # Base de données
    database_url: str = "sqlite:///./axiome.db"
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_recycle: int = 1800   # recycle les connexions après 30 min (évite les coupures serveur)
    db_pool_timeout: int = 30

    # GED (stockage de pièces)
    storage_dir: str = "./storage"
    max_upload_mb: int = 25

    # Sécurité
    secret_key: str = "change-me"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    jwt_algorithm: str = "HS256"

    # Admin initial
    admin_email: str = "admin@axiome.app"
    admin_password: str = "Admin!ChangeMe2026"

    # Éditeur AXIOME (super-administrateur plateforme)
    superadmin_email: str = "editeur@axiome.app"
    superadmin_password: str = "Editeur!ChangeMe2026"

    # E-mail (facultatif : sans SMTP, les messages sont stockés dans la boîte d'envoi)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_expediteur: str = "no-reply@axiome.app"

    # IA
    anthropic_api_key: str = ""

    # Abonnements & paiements
    frontend_url: str = "http://localhost:5173"   # URL publique du front (retours de paiement)
    payment_sandbox: bool = True                  # autorise le « paiement de test » (JAMAIS en production)
    stripe_secret_key: str = ""                   # cartes bancaires (Europe, international)
    fedapay_secret_key: str = ""                  # Mobile Money (Afrique francophone)
    fedapay_env: str = "sandbox"                  # sandbox | live
    stripe_publishable_key: str = ""              # clé publique Stripe (pk_...) : champs carte/IBAN sécurisés côté navigateur
    # Virement bancaire (coordonnées d'AXIOME affichées au payeur ; confirmation manuelle par l'éditeur)
    virement_titulaire: str = ""
    virement_banque: str = ""
    virement_iban: str = ""
    virement_bic: str = ""

    # Journalisation : LOG_FORMAT=json en production (une ligne JSON par événement)
    log_level: str = "INFO"
    log_format: str = "text"

    # Marque
    brand_primary: str = "#0B2545"
    brand_secondary: str = "#C9A227"

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


# Valeurs par défaut interdites en production.
_SECRETS_PAR_DEFAUT = {"change-me", "", "change-me-en-production-secret-tres-long-et-aleatoire"}
_ADMIN_PWD_DEFAUT = "Admin!ChangeMe2026"
_SUPERADMIN_PWD_DEFAUT = {"Editeur!ChangeMe2026", ""}


def verifier_configuration(s: Settings) -> None:
    """Refuse les configurations dangereuses en production (fail-fast au démarrage)."""
    if not s.is_production:
        return
    erreurs: list[str] = []
    if s.secret_key in _SECRETS_PAR_DEFAUT:
        erreurs.append(
            "SECRET_KEY par défaut interdite. "
            "Générez-la : python -c \"import secrets; print(secrets.token_urlsafe(64))\""
        )
    if s.admin_password == _ADMIN_PWD_DEFAUT:
        erreurs.append("ADMIN_PASSWORD par défaut interdit : définissez un mot de passe fort.")
    if s.superadmin_password in _SUPERADMIN_PWD_DEFAUT:
        erreurs.append("SUPERADMIN_PASSWORD par défaut interdit : définissez un mot de passe fort pour le compte éditeur.")
    if s.payment_sandbox:
        erreurs.append("PAYMENT_SANDBOX=true interdit en production (le paiement de test activerait des espaces gratuitement).")
    if s.is_sqlite:
        erreurs.append("SQLite interdit en production : utilisez PostgreSQL (DATABASE_URL=postgresql+psycopg2://…).")
    if erreurs:
        raise RuntimeError("Configuration de production invalide :\n- " + "\n- ".join(erreurs))


@lru_cache
def get_settings() -> Settings:
    """Retourne une instance unique (mémoïsée) des réglages, vérifiée."""
    s = Settings()
    verifier_configuration(s)
    return s


settings = get_settings()
