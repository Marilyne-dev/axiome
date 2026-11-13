"""Génère .env.production avec des secrets aléatoires forts (jamais écrasé sans --force).

    python deploy/generer_secrets.py [--force]

Rotation d'un secret : relancez avec --force (ou éditez la ligne voulue), puis `docker compose up -d`.
  - SECRET_KEY changée : tous les utilisateurs doivent se reconnecter (jetons invalidés) — sans autre effet.
  - POSTGRES_PASSWORD changé : changez-le aussi dans la base :  ALTER USER axiome PASSWORD '…';
  - Mots de passe admin/éditeur : ne s'appliquent qu'à la création des comptes ; changez-les ensuite dans l'application.
Ne commitez JAMAIS .env.production (il est dans .gitignore).
"""
import secrets
import string
import sys
from pathlib import Path

CIBLE = Path(__file__).resolve().parent / ".env.production"
ALPHABET = string.ascii_letters + string.digits + "!@#%^*-_=+"


def mdp(n: int = 24) -> str:
    while True:  # exige majuscule, minuscule, chiffre et symbole
        s = "".join(secrets.choice(ALPHABET) for _ in range(n))
        if (any(c.isupper() for c in s) and any(c.islower() for c in s)
                and any(c.isdigit() for c in s) and any(c in "!@#%^*-_=+" for c in s)):
            return s


def main() -> int:
    if CIBLE.exists() and "--force" not in sys.argv:
        print(f"{CIBLE} existe déjà. Relancez avec --force pour régénérer (les secrets actuels seront perdus).")
        return 1
    pg = secrets.token_urlsafe(24)  # sans caractères spéciaux : utilisé dans l'URL de connexion
    lignes = [
        "# Généré par generer_secrets.py — ne pas commiter",
        f"POSTGRES_PASSWORD={pg}",
        f"SECRET_KEY={secrets.token_urlsafe(64)}",
        "ADMIN_EMAIL=admin@votre-domaine.tld",
        f"ADMIN_PASSWORD={mdp()}",
        "SUPERADMIN_EMAIL=editeur@votre-domaine.tld",
        f"SUPERADMIN_PASSWORD={mdp()}",
        "BASE_URL=https://app.votre-domaine.tld",
        "FRONTEND_URL=https://app.votre-domaine.tld",
        "# Assistant IA (laisser vide pour le désactiver) :",
        "ANTHROPIC_API_KEY=",
        "# Paiements : renseigner les clés de production",
        "STRIPE_SECRET_KEY=", "STRIPE_PUBLISHABLE_KEY=", "FEDAPAY_SECRET_KEY=", "FEDAPAY_ENV=live",
        "# E-mail",
        "SMTP_HOST=", "SMTP_PORT=587", "SMTP_USER=", "SMTP_PASSWORD=",
    ]
    CIBLE.write_text("\n".join(lignes) + "\n", encoding="utf-8")
    try:
        CIBLE.chmod(0o600)
    except OSError:
        pass
    print(f"{CIBLE} créé. Complétez les valeurs « votre-domaine.tld » et les clés externes avant de démarrer.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
