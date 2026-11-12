"""Jeu de démonstration : 1 cabinet, users (dont correspondant LCB-FT),
2 clients (France/PCG/EUR et OHADA/SYSCOHADA/XOF) + 1 mission par client.

Usage :  python -m app.db.seed_data   (exécute init_db au préalable si besoin)
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.db.init_db import init
from app.models.cabinet import Bureau, Cabinet
from app.models.client import Client
from app.models.mission import Cycle, Mission
from app.models.user import Role, User

DEMO_USERS = [
    ("associe@axiome.app", "Associe!2026", "Camille Associé", "ASSOCIE_SIGNATAIRE"),
    ("auditeur@axiome.app", "Auditeur!2026", "Alex Auditeur", "AUDITEUR"),
    ("collab1@axiome.app", "Collab!2026", "Léa Collaboratrice", "COLLABORATEUR"),
    ("collab2@axiome.app", "Collab!2026", "Sam Collaborateur", "COLLABORATEUR"),
    ("lcbft@axiome.app", "Lcbft!2026", "Responsable LCB-FT", "CORRESPONDANT_LCBFT"),
]


def _get_role(db: Session, code: str) -> Role | None:
    return db.query(Role).filter_by(code=code).first()


def seed() -> None:
    init()  # garantit tables + référentiels + devises + RBAC + admin
    db = SessionLocal()
    try:
        cabinet = db.query(Cabinet).filter_by(nom="AXIOME Audit").first()
        if not cabinet:
            cabinet = Cabinet(nom="AXIOME Audit", pays="France", devise_defaut="EUR", referentiel_defaut="PCG_FR")
            db.add(cabinet)
            db.flush()
            db.add(Bureau(cabinet_id=cabinet.id, nom="Siège Paris", ville="Paris", pays="France"))
            db.add(Bureau(cabinet_id=cabinet.id, nom="Bureau Abidjan", ville="Abidjan", pays="Côte d'Ivoire"))

        # Rattacher l'administrateur (créé par init_db sans cabinet) à ce cabinet.
        from app.core.config import settings as _s
        admin = db.query(User).filter_by(email=_s.admin_email).first()
        if admin and admin.cabinet_id is None:
            admin.cabinet_id = cabinet.id

        for email, pwd, nom, role_code in DEMO_USERS:
            if db.query(User).filter_by(email=email).first():
                continue
            u = User(email=email, hashed_password=hash_password(pwd), nom_complet=nom,
                     is_active=True, lang="fr", cabinet_id=cabinet.id)
            role = _get_role(db, role_code)
            if role:
                u.roles.append(role)
            db.add(u)

        # Client France (PCG / EUR)
        c_fr = db.query(Client).filter_by(raison_sociale="Alpha SAS").first()
        if not c_fr:
            c_fr = Client(cabinet_id=cabinet.id, raison_sociale="Alpha SAS",
                          identifiant_legal="812345678", pays="France", secteur="Industrie")
            db.add(c_fr)
            db.flush()
            m = Mission(client_id=c_fr.id, intitule="CAC Alpha SAS — exercice 2025", exercice="2025",
                        referentiel="PCG_FR", pays="France", devise="EUR", statut="planification")
            db.add(m)
            db.flush()
            db.add(Cycle(mission_id=m.id, code="TRESORERIE", libelle="Trésorerie"))
            db.add(Cycle(mission_id=m.id, code="EMPRUNTS", libelle="Emprunts"))

        # Utilisateur "portail client" rattaché à Alpha SAS (démonstration).
        if c_fr and not db.query(User).filter_by(email="portail@axiome.app").first():
            role_client = _get_role(db, "CLIENT")
            up = User(email="portail@axiome.app", hashed_password=hash_password("Portail!2026"),
                      nom_complet="Contact Alpha SAS", is_active=True, lang="fr",
                      cabinet_id=cabinet.id, client_id=c_fr.id)
            if role_client:
                up.roles.append(role_client)
            db.add(up)

        # Client OHADA (SYSCOHADA / XOF)
        c_ci = db.query(Client).filter_by(raison_sociale="Baobab SA").first()
        if not c_ci:
            c_ci = Client(cabinet_id=cabinet.id, raison_sociale="Baobab SA",
                          identifiant_legal="CI-ABJ-2020-B-1234", pays="Côte d'Ivoire", secteur="Négoce")
            db.add(c_ci)
            db.flush()
            m2 = Mission(client_id=c_ci.id, intitule="CAC Baobab SA — exercice 2025", exercice="2025",
                         referentiel="SYSCOHADA_OHADA", pays="Côte d'Ivoire", devise="XOF", statut="acceptation")
            db.add(m2)
            db.flush()
            db.add(Cycle(mission_id=m2.id, code="TRESORERIE", libelle="Trésorerie"))

        db.commit()
        print("[seed_data] OK — cabinet, utilisateurs de démo, clients FR/OHADA et missions créés.")
        print("  Connexions de démo : admin@axiome.app / (voir .env) — associe@ / Associe!2026 — lcbft@ / Lcbft!2026")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
