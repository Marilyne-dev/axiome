"""Logique d'abonnement : offres, inscription d'un cabinet, activation après paiement."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.billing import Abonnement, Paiement, Plan
from app.models.cabinet import Cabinet
from app.models.client import Client
from app.models.mission import Mission
from app.models.user import Role, User, user_roles

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
    """Marque le paiement payé et active (ou prolonge) l'abonnement. Idempotent.

    Si le paiement vise une autre offre (changement d'offre), l'abonnement bascule sur cette offre
    et une nouvelle période démarre immédiatement ; sinon, on prolonge l'échéance actuelle.
    """
    if pay.statut == "paye":
        return
    maintenant = datetime.now(timezone.utc)
    abo = db.get(Abonnement, pay.abonnement_id)
    changement = bool(pay.plan_id) and (pay.plan_id != abo.plan_id or pay.periode != abo.periode)
    if pay.plan_id:
        abo.plan_id, abo.periode = pay.plan_id, pay.periode
    plan = db.get(Plan, abo.plan_id)
    fin_actuelle = _aware(abo.date_fin)
    prolonge = abo.statut == "actif" and fin_actuelle and fin_actuelle > maintenant and not changement
    debut = fin_actuelle if prolonge else maintenant
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


# ------------------------------------------------------------------ quotas
def compter_collaborateurs(db: Session, cabinet_id: int) -> int:
    """Comptes décomptés du quota « collaborateurs » : tous les utilisateurs non archivés du cabinet,
    SAUF l'administrateur (rôle ADMIN). Offre Essentiel (quota 2) = l'administrateur + 2 collaborateurs."""
    admins = (select(user_roles.c.user_id).join(Role, Role.id == user_roles.c.role_id).where(Role.code == "ADMIN"))
    return (db.query(func.count(User.id))
            .filter(User.cabinet_id == cabinet_id, User.is_archived.is_(False), ~User.id.in_(admins))
            .scalar() or 0)


def compter_missions(db: Session, cabinet_id: int) -> int:
    return (db.query(func.count(Mission.id)).join(Client, Mission.client_id == Client.id)
            .filter(Client.cabinet_id == cabinet_id, Mission.is_archived.is_(False)).scalar() or 0)


def incompatibilite(db: Session, cabinet_id: int, plan: Plan) -> str:
    """Raison pour laquelle le cabinet ne peut pas passer à cette offre (usage > quotas), sinon chaîne vide."""
    nb_c, nb_m = compter_collaborateurs(db, cabinet_id), compter_missions(db, cabinet_id)
    raisons = []
    if plan.quota_collaborateurs and nb_c > plan.quota_collaborateurs:
        raisons.append(f"{nb_c} collaborateurs en place pour {plan.quota_collaborateurs} autorisés (archivez-en d'abord)")
    if plan.quota_missions and nb_m > plan.quota_missions:
        raisons.append(f"{nb_m} missions en cours pour {plan.quota_missions} autorisées (archivez-en d'abord)")
    return " ; ".join(raisons)


# ------------------------------------------------------------------ changement d'offre
def _annuler_paiements_non_ouverts(db: Session, abo: Abonnement) -> None:
    """Clôt les paiements en attente dont le payeur n'a encore rien engagé (évite les doublons)."""
    for p in db.query(Paiement).filter_by(abonnement_id=abo.id, statut="en_attente", fournisseur_ref="").all():
        p.statut = "echoue"


def demander_changement(db: Session, abo: Abonnement, plan_code: str, periode: str) -> Paiement:
    """Prépare le paiement d'un changement d'offre (montée ou descente) ou de période (mensuel/annuel).

    L'offre ne change qu'une fois le paiement confirmé par le fournisseur (voir `activer`).
    Une descente est refusée si l'usage actuel dépasse les quotas de la nouvelle offre.
    """
    if abo.statut in ("suspendu", "resilie"):
        raise HTTPException(status.HTTP_409_CONFLICT, "Abonnement suspendu ou résilié : contactez AXIOME.")
    if periode not in PERIODES:
        raise HTTPException(422, "Période invalide")
    plan = db.query(Plan).filter_by(code=plan_code, is_active=True).first()
    if not plan:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Offre introuvable")
    if plan.id == abo.plan_id and periode == abo.periode:
        raise HTTPException(status.HTTP_409_CONFLICT, "Vous êtes déjà sur cette offre : utilisez « Renouveler ».")
    raison = incompatibilite(db, abo.cabinet_id, plan)
    if raison:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Changement impossible : {raison}.")
    _annuler_paiements_non_ouverts(db, abo)
    if abo.statut == "en_attente_paiement":          # rien n'a encore été payé : on remplace simplement le choix
        abo.plan_id, abo.periode = plan.id, periode
        pay = nouveau_paiement(db, abo, plan)
    else:
        pay = Paiement(reference=uuid.uuid4().hex, abonnement_id=abo.id, plan_id=plan.id,
                       montant=prix(plan, periode, abo.devise), devise=abo.devise, periode=periode)
        db.add(pay); db.flush()
    db.commit()
    return pay


def offres_pour_cabinet(db: Session, abo: Abonnement) -> list[dict]:
    """Offres actives avec, pour chacune, la possibilité de changement depuis l'abonnement actuel."""
    out = []
    for p in liste_plans(db):
        d = plan_public(p)
        raison = "" if p.id == abo.plan_id else incompatibilite(db, abo.cabinet_id, p)
        d.update(actuelle=p.id == abo.plan_id, periode_actuelle=abo.periode if p.id == abo.plan_id else None,
                 possible=not raison, raison=raison, devise=abo.devise)
        out.append(d)
    return out


# ------------------------------------------------------------------ console éditeur : offres et suivi
def lignes_abonnements(db: Session) -> list[dict]:
    """Un abonnement par cabinet : offre, statut réel, échéance, dernier paiement, paiements en attente."""
    out = []
    maintenant = datetime.now(timezone.utc)
    for cab in db.query(Cabinet).order_by(Cabinet.nom).all():
        abo = abonnement_du_cabinet(db, cab.id)
        if abo is None:
            out.append({"cabinet": cab, "abo": None, "plan": None, "statut": "sans_abonnement", "jours": None,
                        "dernier": None, "en_attente": 0})
            continue
        fin = _aware(abo.date_fin)
        pays = db.query(Paiement).filter_by(abonnement_id=abo.id).order_by(Paiement.id.desc()).all()
        out.append({"cabinet": cab, "abo": abo, "plan": db.get(Plan, abo.plan_id), "statut": statut_effectif(abo),
                    "jours": (fin - maintenant).days if fin else None,
                    "dernier": next((p for p in pays if p.statut == "paye"), None),
                    "en_attente": sum(1 for p in pays if p.statut == "en_attente")})
    return out


def derniers_paiements(db: Session, limite: int = 100) -> list[dict]:
    out = []
    for p in db.query(Paiement).order_by(Paiement.id.desc()).limit(limite).all():
        abo = db.get(Abonnement, p.abonnement_id)
        cab = db.get(Cabinet, abo.cabinet_id) if abo else None
        plan = db.get(Plan, p.plan_id or (abo.plan_id if abo else 0))
        out.append({"p": p, "cabinet": cab.nom if cab else "—", "plan": plan.nom if plan else "—",
                    "changement": bool(p.plan_id)})
    return out


def _entier(v, nom: str, minimum: int = 0) -> int:
    try:
        n = int(v)
    except (TypeError, ValueError) as exc:
        raise HTTPException(422, f"{nom} : nombre entier attendu") from exc
    if n < minimum:
        raise HTTPException(422, f"{nom} : doit être ≥ {minimum}")
    return n


def _centimes(v, nom: str) -> int:
    """Prix saisi en euros (virgule ou point acceptés) -> centimes."""
    try:
        n = round(float(str(v).replace(",", ".").replace(" ", "")) * 100)
    except ValueError as exc:
        raise HTTPException(422, f"{nom} : montant invalide") from exc
    if n < 0:
        raise HTTPException(422, f"{nom} : doit être ≥ 0")
    return n


def enregistrer_plan(db: Session, plan: Plan | None, *, code: str = "", nom: str, description: str, fonctionnalites: str,
                     prix_mensuel_eur, prix_annuel_eur, prix_mensuel_xof, prix_annuel_xof,
                     quota_collaborateurs, quota_missions, ordre, is_featured: bool, is_active: bool,
                     appliquer_aux_cabinets: bool = False) -> Plan:
    """Crée ou modifie une offre. Les prix s'appliquent aux PROCHAINS paiements (jamais rétroactivement).
    `appliquer_aux_cabinets` répercute en plus les quotas sur les cabinets déjà abonnés à cette offre."""
    if not nom.strip():
        raise HTTPException(422, "Nom de l'offre requis")
    if plan is None:
        code = code.strip().lower()
        if not code or not code.replace("_", "").replace("-", "").isalnum():
            raise HTTPException(422, "Code de l'offre invalide (lettres, chiffres, - et _)")
        if db.query(Plan).filter_by(code=code).first():
            raise HTTPException(status.HTTP_409_CONFLICT, "Ce code d'offre existe déjà")
        plan = Plan(code=code, nom=nom.strip())
        db.add(plan)
    lignes = [l.strip() for l in (fonctionnalites or "").splitlines() if l.strip()]
    plan.nom, plan.description = nom.strip(), (description or "").strip()[:255]
    plan.fonctionnalites = json.dumps(lignes, ensure_ascii=False)
    plan.prix_mensuel_eur = _centimes(prix_mensuel_eur, "Prix mensuel EUR")
    plan.prix_annuel_eur = _centimes(prix_annuel_eur, "Prix annuel EUR")
    plan.prix_mensuel_xof = _entier(prix_mensuel_xof, "Prix mensuel XOF")
    plan.prix_annuel_xof = _entier(prix_annuel_xof, "Prix annuel XOF")
    plan.quota_collaborateurs = _entier(quota_collaborateurs, "Quota collaborateurs")
    plan.quota_missions = _entier(quota_missions, "Quota missions")
    plan.ordre = _entier(ordre, "Ordre")
    plan.is_featured, plan.is_active = is_featured, is_active
    db.flush()
    if appliquer_aux_cabinets:
        for abo in db.query(Abonnement).filter(Abonnement.plan_id == plan.id,
                                               Abonnement.statut.in_(("actif", "en_attente_paiement"))).all():
            cab = db.get(Cabinet, abo.cabinet_id)
            cab.quota_collaborateurs, cab.quota_missions = plan.quota_collaborateurs, plan.quota_missions
    db.commit()
    return plan
