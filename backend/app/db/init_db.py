"""Initialisation de la base : tables, référentiels, devises ISO 4217, RBAC, admin.

Idempotent : peut être relancé sans dupliquer les données de référence.
Usage :  python -m app.db.init_db
"""
from __future__ import annotations

from sqlalchemy.orm import Session

import app.models  # enregistre toutes les tables sur Base  # noqa: F401
from app.core.config import settings
from app.core.database import SessionLocal, engine
from app.core.security import hash_password
from app.db.iso4217 import iter_iso4217
from app.models.base import Base
from app.models.devise import Devise
from app.models.referentiel import Referentiel, RegleFiscale
from app.models.user import Permission, Role, User
from app.services import billing_service

# --- Référentiels actifs par défaut ---
REFERENTIELS = [
    {"code": "PCG_FR", "libelle": "Plan Comptable Général (France)", "zone": "France", "norme_rapport": "NEP"},
    {"code": "IFRS", "libelle": "IFRS (IASB)", "zone": "International", "norme_rapport": "ISA"},
    {"code": "SYSCOHADA_OHADA", "libelle": "SYSCOHADA révisé (OHADA)", "zone": "OHADA", "norme_rapport": "ISA"},
]

# --- Règles fiscales d'amorçage (paramétrables, jamais en dur ailleurs) ---
REGLES = [
    ("PCG_FR", "France", "TVA_NORMALE", "TVA taux normal", 0.20),
    ("PCG_FR", "France", "IS_STD", "Impôt sociétés (taux normal)", 0.25),
    ("SYSCOHADA_OHADA", "Côte d'Ivoire", "TVA_NORMALE", "TVA taux normal", 0.18),
]

# --- RBAC : rôles et permissions ---
ROLES = {
    "SUPERADMIN": "Éditeur AXIOME (super-administrateur)",
    "ADMIN": "Administrateur du cabinet",
    "ASSOCIE_SIGNATAIRE": "Associé signataire",
    "AUDITEUR": "Auditeur",
    "COLLABORATEUR": "Collaborateur",
    "CORRESPONDANT_LCBFT": "Correspondant LCB-FT",
    "CLIENT": "Client (portail)",
}

PERMISSIONS = [
    "platform:manage", "cabinet:manage", "user:manage", "client:read", "client:write",
    "mission:read", "mission:write", "cycle:read", "cycle:write",
    "report:generate", "lcbft:read", "lcbft:declare",
]

# Attribution rôle -> permissions (ADMIN et SUPERADMIN ont tout via garde applicative).
ROLE_PERMS = {
    "SUPERADMIN": set(PERMISSIONS),
    "ASSOCIE_SIGNATAIRE": {"client:read", "mission:read", "mission:write", "report:generate", "cycle:read", "cycle:write"},
    "AUDITEUR": {"client:read", "mission:read", "cycle:read", "cycle:write"},
    "COLLABORATEUR": {"client:read", "mission:read", "cycle:read"},
    "CORRESPONDANT_LCBFT": {"client:read", "lcbft:read", "lcbft:declare"},
    "CLIENT": set(),  # accès restreint au portail uniquement
}


def _seed_referentiels(db: Session) -> None:
    for r in REFERENTIELS:
        if not db.query(Referentiel).filter_by(code=r["code"]).first():
            db.add(Referentiel(**r))
    for ref, pays, code, lib, taux in REGLES:
        exists = db.query(RegleFiscale).filter_by(referentiel_code=ref, pays=pays, code=code).first()
        if not exists:
            db.add(RegleFiscale(referentiel_code=ref, pays=pays, code=code, libelle=lib, taux=taux))


def _seed_devises(db: Session) -> int:
    existing = {d.code for d in db.query(Devise.code).all()}
    added = 0
    for d in iter_iso4217():
        if d["code"] not in existing:
            db.add(Devise(**d))
            added += 1
    return added


def _seed_rbac(db: Session) -> None:
    perms: dict[str, Permission] = {}
    for code in PERMISSIONS:
        p = db.query(Permission).filter_by(code=code).first()
        if not p:
            p = Permission(code=code, description=code)
            db.add(p)
        perms[code] = p
    db.flush()
    for code, libelle in ROLES.items():
        role = db.query(Role).filter_by(code=code).first()
        if not role:
            role = Role(code=code, libelle=libelle)
            db.add(role)
        role.permissions = [perms[c] for c in ROLE_PERMS.get(code, set())]
    db.flush()


def _seed_admin(db: Session) -> None:
    if db.query(User).filter_by(email=settings.admin_email).first():
        return
    admin_role = db.query(Role).filter_by(code="ADMIN").first()
    admin = User(
        email=settings.admin_email,
        hashed_password=hash_password(settings.admin_password),
        nom_complet="Administrateur AXIOME",
        is_active=True,
        lang=settings.default_lang,
    )
    if admin_role:
        admin.roles.append(admin_role)
    db.add(admin)


def _seed_superadmin(db: Session) -> None:
    """Compte éditeur AXIOME (super-administrateur plateforme, sans cabinet)."""
    if db.query(User).filter_by(email=settings.superadmin_email).first():
        return
    role = db.query(Role).filter_by(code="SUPERADMIN").first()
    editeur = User(
        email=settings.superadmin_email,
        hashed_password=hash_password(settings.superadmin_password),
        nom_complet="Éditeur AXIOME",
        is_active=True,
        lang=settings.default_lang,
    )
    if role:
        editeur.roles.append(role)
    db.add(editeur)


def init() -> None:
    """Crée les tables et charge les données de référence (idempotent)."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        _seed_referentiels(db)
        nb_dev = _seed_devises(db)
        _seed_rbac(db)
        _seed_admin(db)
        _seed_superadmin(db)
        billing_service.seed_plans(db)
        db.commit()
        total_dev = db.query(Devise).count()
        print(f"[init_db] OK — {total_dev} devises ISO 4217 en base (+{nb_dev} ajoutées), "
              f"référentiels + RBAC + admin '{settings.admin_email}' prêts.")
    finally:
        db.close()


if __name__ == "__main__":
    init()
