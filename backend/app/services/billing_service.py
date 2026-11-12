"""Logique d'abonnement : offres, inscription d'un cabinet, activation après paiement."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.billing import Abonnement, Paiement, Plan
from app.models.cabinet import Cabinet
from app.models.user import Role, User

PERIODES = {"mensuel": 30, "annuel": 365}
DEVISES = ("EUR", "XOF")

# Offres initiales (prix de départ, modifiables ensuite en base). EUR en centimes.
PLANS_INITIAUX = [
    dict(code="essentiel", nom="Essentiel", ordre=1, description="Pour un petit cabinet qui démarre.",
         prix_mensuel_eur=4900, prix_annuel_eur=49000, prix_mensuel_xof=32000, prix_annuel_xof=320000,
         quota_collaborateurs=2, quota_missions=5,
         fonctionnalites=["2 comptes commissaires aux comptes", "5 missions en cours", "Import FEC et revue analytique",
                          "Cartographie des risques", "Rapports Word et PDF"]),
    dict(code="cabinet", nom="Cabinet", ordre=2, is_featured=True, description="Pour un cabinet en pleine activité.",
         prix_mensuel_eur=14900, prix_annuel_eur=149000, prix_mensuel_xof=98000, prix_annuel_xof=980000,
         quota_collaborateurs=10, quota_missions=30,
         fonctionnalites=["10 comptes commissaires aux comptes", "30 missions en cours", "Tous les modules d'audit",
                          "Confirmations externes et échantillonnage", "Conformité LCB-FT", "Support prioritaire"]),
    dict(code="reseau", nom="Réseau", ordre=3, description="Pour les réseaux et grands cabinets.",
         prix_mensuel_eur=39900, prix_annuel_eur=399000, prix_mensuel_xof=262000, prix_annuel_xof=2620000,
         quota_collaborateurs=0, quota_missions=0,
         fonctionnalites=["Comptes illimités", "Missions illimitées", "Multi-bureaux et multi-pays",
                          "Multi-référentiels PCG, IFRS, SYSCOHADA", "Accompagnement dédié"]),
]


def seed_plans(db: Session) -> None:
    """Crée les offres initiales si absentes (n'écrase jamais des prix modifiés)."""
    for d in PLANS_INITIAUX:
        if not db.query(Plan).filter_by(code=d["code"]).first():
            d = dict(d); d["fonctionnalites"] = json.dumps(d["fonctionnalites"], ensure_ascii=False)
            db.add(Plan(**d))
    db.flush()


def _aware(dt: datetime | None) -> datetime | None:
    """Rend une date comparable (SQLite renvoie des dates sans fuseau, PostgreSQL avec)."""
    return dt if dt is None or dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def prix(plan: Plan, periode: str, devise: str) -> int:
    return getattr(plan, f"prix_{'mensuel' if periode == 'mensuel' else 'annuel'}_{devise.lower()}")


def plan_public(plan: Plan) -> dict:
    return {
        "code": plan.code, "nom": plan.nom, "description": plan.description, "featured": plan.is_featured,
        "quota_collaborateurs": plan.quota_collaborateurs, "quota_missions": plan.quota_missions,
        "fonctionnalites": json.loads(plan.fonctionnalites or "[]"),
        "prix": {"EUR": {"mensuel": plan.prix_mensuel_eur, "annuel": plan.prix_annuel_eur},
                 "XOF": {"mensuel": plan.prix_mensuel_xof, "annuel": plan.prix_annuel_xof}},
    }


def liste_plans(db: Session) -> list[Plan]:
    return db.query(Plan).filter(Plan.is_active.is_(True)).order_by(Plan.ordre).all()


def _mot_de_passe_valide(pwd: str) -> bool:
    return len(pwd) >= 10 and any(c.isalpha() for c in pwd) and any(c.isdigit() for c in pwd)


def inscrire(db: Session, *, plan_code: str, periode: str, devise: str, cabinet_nom: str, pays: str,
             admin_nom: str, admin_email: str, admin_password: str) -> tuple[Abonnement, Paiement]:
    """Crée cabinet + administrateur + abonnement « en attente de paiement » + paiement à régler."""
    plan = db.query(Plan).filter_by(code=plan_code, is_active=True).first()
    if not plan:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Offre introuvable")
    if periode not in PERIODES or devise not in DEVISES:
        raise HTTPException(422, "Période ou devise invalide")
    if not _mot_de_passe_valide(admin_password):
        raise HTTPException(422,
                            "Mot de passe trop faible : 10 caractères minimum, avec lettres et chiffres.")
    email = admin_email.strip().lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Un compte existe déjà avec cet e-mail. Connectez-vous.")

    cab = Cabinet(nom=cabinet_nom.strip(), pays=pays.strip() or "France", devise_defaut=devise,
                  referentiel_defaut="SYSCOHADA_OHADA" if devise == "XOF" else "PCG_FR",
                  quota_collaborateurs=plan.quota_collaborateurs, quota_missions=plan.quota_missions)
    db.add(cab); db.flush()
    admin = User(email=email, hashed_password=hash_password(admin_password), nom_complet=admin_nom.strip(),
                 is_active=True, cabinet_id=cab.id)
    admin.roles.append(db.query(Role).filter_by(code="ADMIN").one())
    db.add(admin)
    abo = Abonnement(cabinet_id=cab.id, plan_id=plan.id, statut="en_attente_paiement", periode=periode, devise=devise)
    db.add(abo); db.flush()
    pay = nouveau_paiement(db, abo, plan)
    db.commit()
    return abo, pay


def nouveau_paiement(db: Session, abo: Abonnement, plan: Plan | None = None) -> Paiement:
    plan = plan or db.get(Plan, abo.plan_id)
    pay = Paiement(reference=uuid.uuid4().hex, abonnement_id=abo.id, montant=prix(plan, abo.periode, abo.devise),
                   devise=abo.devise, periode=abo.periode)
    db.add(pay); db.flush()
    return pay


def activer(db: Session, pay: Paiement) -> None:
    """Marque le paiement payé et active (ou prolonge) l'abonnement. Idempotent."""
    if pay.statut == "paye":
        return
    maintenant = datetime.now(timezone.utc)
    abo = db.get(Abonnement, pay.abonnement_id)
    plan = db.get(Plan, abo.plan_id)
    fin_actuelle = _aware(abo.date_fin)
    debut = fin_actuelle if abo.statut == "actif" and fin_actuelle and fin_actuelle > maintenant else maintenant
    pay.statut, pay.paye_le = "paye", maintenant
    abo.statut, abo.date_debut = "actif", abo.date_debut or maintenant
    abo.date_fin = debut + timedelta(days=PERIODES[pay.periode])
    cab = db.get(Cabinet, abo.cabinet_id)
    cab.quota_collaborateurs, cab.quota_missions, cab.is_archived = plan.quota_collaborateurs, plan.quota_missions, False
    db.commit()


def statut_effectif(abo: Abonnement | None) -> str:
    """Statut réel. Cabinet sans abonnement (créé par l'éditeur) = actif. Échéance dépassée = expire."""
    if abo is None:
        return "actif"
    if abo.statut == "actif" and abo.date_fin:
        if _aware(abo.date_fin) < datetime.now(timezone.utc):
            return "expire"
    return abo.statut


def abonnement_du_cabinet(db: Session, cabinet_id: int | None) -> Abonnement | None:
    return db.query(Abonnement).filter_by(cabinet_id=cabinet_id).first() if cabinet_id else None
