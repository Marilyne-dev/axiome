"""API de l'espace cabinet (front React) : tableau de bord, clients, missions.

Toutes les données sont cloisonnées au cabinet de l'utilisateur connecté.
Un utilisateur sans cabinet (ex. éditeur, compte non rattaché) reçoit `cabinet: null`
et des listes vides, jamais les données d'un autre cabinet.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.routes_public import ouvrir_paiement
from app.api.scope import mission_du_cabinet
from app.core.database import get_db
from app.core.missions_ref import CATEGORIES, TYPES_MISSION
from app.core.missions_ref import type_mission as _type_def
from app.models.audit import RiskItem, Threshold
from app.models.balance import LigneBalance
from app.models.billing import Paiement, Plan
from app.models.cabinet import Cabinet
from app.models.client import Client
from app.models.mission import Cycle, Mission, MissionDiligence
from app.models.referentiel import Referentiel
from app.models.user import User
from app.services import billing_service, controles_service, pilotage_service
from app.services import payment_providers as pp
from app.services.audit_service import journaliser

router = APIRouter(prefix="/espace", tags=["espace"])


def _utilisateur_cabinet(user: User = Depends(get_current_user)) -> User:
    """Interdit l'espace cabinet au portail de l'entité auditée (rôle CLIENT)."""
    if user.has_role("CLIENT"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Espace réservé aux cabinets")
    return user


def _abonnement_info(db: Session, user: User) -> dict | None:
    abo = billing_service.abonnement_du_cabinet(db, user.cabinet_id)
    if abo is None:
        return {"statut": "actif", "plan": None, "date_fin": None}      # cabinet créé par l'éditeur
    plan = db.get(Plan, abo.plan_id)
    return {"statut": billing_service.statut_effectif(abo), "plan": plan.nom if plan else None,
            "plan_code": plan.code if plan else None, "periode": abo.periode, "devise": abo.devise,
            "date_fin": abo.date_fin.isoformat() if abo.date_fin else None}


def _acces_actif(db: Session = Depends(get_db), user: User = Depends(_utilisateur_cabinet)) -> User:
    """Les données du cabinet ne sont accessibles qu'avec un abonnement actif (402 sinon)."""
    if user.cabinet_id and billing_service.statut_effectif(billing_service.abonnement_du_cabinet(db, user.cabinet_id)) != "actif":
        raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, "abonnement_inactif")
    return user


def _ligne_mission(l: dict) -> dict:
    m: Mission = l["mission"]
    return {
        "id": m.id, "intitule": m.intitule, "exercice": m.exercice,
        "client": m.client.raison_sociale if m.client else "",
        "type_mission": m.type_mission, "statut": m.statut,
        "referentiel": m.referentiel, "devise": m.devise,
        "avancement": l["avancement"], "risque_max": l["risque_max"],
        "nb_anomalies": l["nb_anomalies"], "ci_deficients": l["ci_deficients"],
    }


def _infos_cabinet(db: Session, user: User, nb_missions: int) -> dict | None:
    if not user.cabinet_id:
        return None
    cab = db.get(Cabinet, user.cabinet_id)
    if not cab or cab.is_archived:
        return None
    nb_collab = billing_service.compter_collaborateurs(db, cab.id)     # l'administrateur n'est pas décompté
    return {
        "nom": cab.nom, "pays": cab.pays, "devise": cab.devise_defaut,
        "referentiel": cab.referentiel_defaut,
        "collaborateurs": {"utilises": nb_collab, "quota": cab.quota_collaborateurs},  # quota 0 = illimité
        "missions": {"utilises": nb_missions, "quota": cab.quota_missions},
    }


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), user: User = Depends(_utilisateur_cabinet)) -> dict:
    """Indicateurs du cabinet : clients, missions, risques, anomalies, quotas."""
    abo = _abonnement_info(db, user) if user.cabinet_id else None
    if abo and abo["statut"] != "actif":     # espace verrouillé : on n'expose que l'état de l'abonnement
        return {"cabinet": _infos_cabinet(db, user, 0), "abonnement": abo, "verrouille": True,
                "kpis": {"clients": 0, "missions": 0, "anomalies": 0, "avancement_moyen": 0},
                "risques_par_niveau": {}, "par_referentiel": {}, "missions": []}
    if not user.cabinet_id:
        return {"cabinet": None, "kpis": {"clients": 0, "missions": 0, "anomalies": 0, "avancement_moyen": 0},
                "risques_par_niveau": {}, "par_referentiel": {}, "missions": []}
    s = pilotage_service.synthese(db, user.cabinet_id)
    lignes = [_ligne_mission(l) for l in s["lignes"]]
    avancement = round(sum(l["avancement"] for l in lignes) / len(lignes)) if lignes else 0
    return {
        "cabinet": _infos_cabinet(db, user, s["nb_missions"]), "abonnement": abo, "verrouille": False,
        "kpis": {"clients": s["nb_clients"], "missions": s["nb_missions"],
                 "anomalies": s["missions_avec_anomalies"], "avancement_moyen": avancement},
        "risques_par_niveau": s["risques_par_niveau"],
        "par_referentiel": s["par_referentiel"],
        "missions": lignes[:8],
    }


@router.get("/clients")
def clients(q: str = "", db: Session = Depends(get_db), user: User = Depends(_acces_actif)) -> list[dict]:
    if not user.cabinet_id:
        return []
    req = db.query(Client).filter(Client.cabinet_id == user.cabinet_id, Client.is_archived.is_(False))
    if q.strip():
        req = req.filter(Client.raison_sociale.ilike(f"%{q.strip()}%"))
    out = []
    for c in req.order_by(Client.raison_sociale).all():
        nb = db.query(func.count(Mission.id)).filter(Mission.client_id == c.id, Mission.is_archived.is_(False)).scalar() or 0
        out.append({"id": c.id, "raison_sociale": c.raison_sociale, "identifiant_legal": c.identifiant_legal,
                    "pays": c.pays, "secteur": c.secteur, "nb_missions": nb})
    return out


@router.get("/missions")
def missions(db: Session = Depends(get_db), user: User = Depends(_acces_actif)) -> list[dict]:
    if not user.cabinet_id:
        return []
    return [_ligne_mission(l) for l in pilotage_service.synthese(db, user.cabinet_id)["lignes"]]


@router.get("/abonnement")
def abonnement(db: Session = Depends(get_db), user: User = Depends(_utilisateur_cabinet)) -> dict:
    """Offre, état, échéance et historique des paiements du cabinet."""
    abo = billing_service.abonnement_du_cabinet(db, user.cabinet_id)
    if abo is None:
        return {"abonnement": _abonnement_info(db, user) if user.cabinet_id else None, "paiements": [], "peut_payer": False}
    paiements = (db.query(Paiement).filter_by(abonnement_id=abo.id).order_by(Paiement.id.desc()).limit(20).all())
    return {"abonnement": _abonnement_info(db, user),
            "paiements": [{"reference": p.reference, "montant": p.montant, "devise": p.devise, "periode": p.periode,
                           "statut": p.statut, "date": (p.paye_le or p.created_at).isoformat()} for p in paiements],
            "peut_payer": user.has_role("ADMIN"), "peut_changer": user.has_role("ADMIN") and abo.statut not in ("suspendu", "resilie")}


@router.post("/abonnement/payer")
def payer(db: Session = Depends(get_db), user: User = Depends(_utilisateur_cabinet)) -> dict:
    """Ouvre un paiement pour activer ou renouveler l'abonnement (administrateur du cabinet)."""
    if not user.has_role("ADMIN"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Réservé à l'administrateur du cabinet")
    abo = billing_service.abonnement_du_cabinet(db, user.cabinet_id)
    if abo is None or abo.statut in ("suspendu", "resilie"):
        raise HTTPException(status.HTTP_409_CONFLICT, "Aucun abonnement à régler. Contactez AXIOME.")
    pay = billing_service.nouveau_paiement(db, abo)
    db.commit()
    try:
        url = ouvrir_paiement(db, pay, user.email, user.nom_complet or user.email)
    except pp.ErreurPaiement as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
    return {"checkout_url": url, "reference": pay.reference}


class ChangerOffreIn(BaseModel):
    plan_code: str = Field(min_length=1, max_length=30)
    periode: str = Field(default="mensuel", pattern="^(mensuel|annuel)$")


@router.get("/offres")
def offres(db: Session = Depends(get_db), user: User = Depends(_utilisateur_cabinet)) -> dict:
    """Offres disponibles pour ce cabinet, avec la possibilité de changer (quotas respectés) pour chacune."""
    abo = billing_service.abonnement_du_cabinet(db, user.cabinet_id)
    if abo is None:
        return {"offres": [], "peut_changer": False}
    return {"offres": billing_service.offres_pour_cabinet(db, abo),
            "peut_changer": user.has_role("ADMIN") and abo.statut not in ("suspendu", "resilie")}


@router.post("/abonnement/changer-offre")
def changer_offre(data: ChangerOffreIn, db: Session = Depends(get_db), user: User = Depends(_utilisateur_cabinet)) -> dict:
    """Ouvre le paiement d'un changement d'offre (montée/descente) ou de période. Administrateur du cabinet uniquement.

    L'offre ne change qu'une fois le paiement confirmé ; la nouvelle période démarre alors immédiatement.
    """
    if not user.has_role("ADMIN"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Réservé à l'administrateur du cabinet")
    abo = billing_service.abonnement_du_cabinet(db, user.cabinet_id)
    if abo is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Aucun abonnement à modifier. Contactez AXIOME.")
    pay = billing_service.demander_changement(db, abo, data.plan_code, data.periode)
    journaliser(db, user_id=user.id, action="abonnement.changer_offre", objet="abonnement",
                detail=f"{data.plan_code}/{data.periode}")
    db.commit()
    try:
        url = ouvrir_paiement(db, pay, user.email, user.nom_complet or user.email)
    except pp.ErreurPaiement as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
    return {"checkout_url": url, "reference": pay.reference, "montant": pay.montant, "devise": pay.devise}


# ------------------------------------------------------------------ création client / mission, détail mission
class ClientIn(BaseModel):
    raison_sociale: str = Field(min_length=2, max_length=200)
    identifiant_legal: str = Field(default="", max_length=60)
    pays: str = Field(default="France", max_length=80)
    secteur: str = Field(default="", max_length=120)


class MissionIn(BaseModel):
    client_id: int
    intitule: str = Field(min_length=2, max_length=200)
    exercice: str = Field(default="", max_length=9)
    type_mission: str = "CERT_ANNUELS"
    referentiel: str = "PCG_FR"
    devise: str = Field(default="EUR", min_length=3, max_length=3)


@router.post("/clients", status_code=status.HTTP_201_CREATED)
def creer_client(data: ClientIn, db: Session = Depends(get_db), user: User = Depends(_acces_actif)) -> dict:
    if not user.cabinet_id:
        raise HTTPException(status.HTTP_409_CONFLICT, "Utilisateur sans cabinet rattaché.")
    c = Client(cabinet_id=user.cabinet_id, raison_sociale=data.raison_sociale.strip(),
               identifiant_legal=data.identifiant_legal.strip(), pays=data.pays.strip() or "France",
               secteur=data.secteur.strip())
    db.add(c)
    journaliser(db, user_id=user.id, action="client.creer", objet="client", detail=c.raison_sociale)
    db.commit()
    return {"id": c.id, "raison_sociale": c.raison_sociale}


@router.get("/referentiels-types")
def options_mission(db: Session = Depends(get_db), user: User = Depends(_acces_actif)) -> dict:
    """Listes de choix du formulaire « Nouvelle mission »."""
    refs = db.query(Referentiel).filter(Referentiel.actif.is_(True)).order_by(Referentiel.code).all()
    return {"referentiels": [{"code": r.code, "libelle": r.libelle} for r in refs],
            "types": [{"categorie": lib, "types": [{"code": c, "libelle": d["libelle"]} for c, d in TYPES_MISSION.items()
                                                   if d["categorie"] == cat]} for cat, lib in CATEGORIES]}


@router.post("/missions", status_code=status.HTTP_201_CREATED)
def creer_mission(data: MissionIn, db: Session = Depends(get_db), user: User = Depends(_acces_actif)) -> dict:
    if not user.cabinet_id:
        raise HTTPException(status.HTTP_409_CONFLICT, "Utilisateur sans cabinet rattaché.")
    client = db.get(Client, data.client_id)
    if not client or client.cabinet_id != user.cabinet_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Client introuvable")
    ref = db.query(Referentiel).filter_by(code=data.referentiel, actif=True).first()
    if not ref:
        raise HTTPException(422, "Référentiel inconnu")
    if data.type_mission not in TYPES_MISSION:
        raise HTTPException(422, "Type de mission inconnu")
    cab = db.get(Cabinet, user.cabinet_id)
    if cab and cab.quota_missions:
        nb = billing_service.compter_missions(db, user.cabinet_id)
        if nb >= cab.quota_missions:
            raise HTTPException(status.HTTP_409_CONFLICT, "Quota de missions atteint pour votre offre.")
    m = Mission(client_id=client.id, intitule=data.intitule.strip(), exercice=data.exercice.strip(),
                type_mission=data.type_mission, referentiel=ref.code, devise=data.devise.upper(),
                pays=client.pays or "France")
    db.add(m)
    journaliser(db, user_id=user.id, action="mission.creer", objet="mission", detail=f"{m.intitule} [{m.type_mission}]")
    db.commit()
    return {"id": m.id}


PHASES = ["acceptation", "planification", "realisation", "finalisation"]


def _diligences(db: Session, m: Mission) -> list[MissionDiligence]:
    """Checklist propre au type de mission (créée / synchronisée à la première lecture)."""
    attendues = _type_def(m.type_mission)["diligences"]
    rows = db.query(MissionDiligence).filter_by(mission_id=m.id).order_by(MissionDiligence.id).all()
    if [d.libelle for d in rows] != attendues:
        for d in rows:
            db.delete(d)
        db.flush()
        for i, lib in enumerate(attendues):
            db.add(MissionDiligence(mission_id=m.id, code=str(i), libelle=lib, fait=False))
        db.commit()
        rows = db.query(MissionDiligence).filter_by(mission_id=m.id).order_by(MissionDiligence.id).all()
    return rows


@router.get("/missions/{mission_id}")
def detail_mission(mission_id: int, db: Session = Depends(get_db), user: User = Depends(_utilisateur_cabinet)) -> dict:
    m = mission_du_cabinet(db, user, mission_id)
    tdef = _type_def(m.type_mission)
    lignes = db.query(LigneBalance).filter_by(mission_id=m.id).count()
    seuils = db.query(Threshold).filter_by(mission_id=m.id).first()
    dil = _diligences(db, m)
    cycles = db.query(Cycle).filter_by(mission_id=m.id).order_by(Cycle.id).all()
    return {
        "id": m.id, "intitule": m.intitule, "exercice": m.exercice, "type_mission": m.type_mission,
        "type_libelle": tdef["libelle"], "base_normative": tdef.get("base", ""), "livrable": tdef.get("livrable", ""),
        "referentiel": m.referentiel, "pays": m.pays, "devise": m.devise, "statut": m.statut,
        "client": {"id": m.client_id, "raison_sociale": m.client.raison_sociale if m.client else ""},
        "balance": {"nb_lignes": lignes},
        "seuils": ({"signification": seuils.seuil_signification, "planification": seuils.seuil_planification,
                    "remontee": seuils.seuil_remontee, "base": seuils.base_retenue} if seuils else None),
        "nb_risques": db.query(func.count(RiskItem.id)).filter_by(mission_id=m.id).scalar() or 0,
        "diligences": [{"id": d.id, "libelle": d.libelle, "fait": d.fait} for d in dil],
        "cycles": [{"id": c.id, "code": c.code, "libelle": c.libelle, "statut": c.statut} for c in cycles],
    }


@router.patch("/missions/{mission_id}/diligences/{did}")
def basculer_diligence(mission_id: int, did: int, db: Session = Depends(get_db), user: User = Depends(_utilisateur_cabinet)) -> dict:
    m = mission_du_cabinet(db, user, mission_id)
    d = db.get(MissionDiligence, did)
    if not d or d.mission_id != m.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Diligence introuvable")
    d.fait = not d.fait
    db.commit()
    return {"id": d.id, "fait": d.fait}


@router.get("/missions/{mission_id}/controles")
def controles_balance(mission_id: int, db: Session = Depends(get_db), user: User = Depends(_utilisateur_cabinet)) -> dict:
    """Contrôles d'équilibre et de cohérence de la balance importée."""
    m = mission_du_cabinet(db, user, mission_id)
    lignes = db.query(LigneBalance).filter_by(mission_id=m.id).all()
    return controles_service.controler(lignes) if lignes else {"controles": [], "nb_anomalies": 0}


@router.get("/collaborateurs")
def collaborateurs(db: Session = Depends(get_db), user: User = Depends(_acces_actif)) -> list[dict]:
    """Collaborateurs actifs du cabinet (affectation d'équipe). Cloisonné au cabinet de l'utilisateur."""
    if not user.cabinet_id:
        return []
    rows = (db.query(User).filter(User.cabinet_id == user.cabinet_id, User.is_archived.is_(False),
                                  User.is_active.is_(True)).order_by(User.nom_complet, User.email).all())
    return [{"id": u.id, "nom": u.nom_complet or u.email, "email": u.email, "roles": [r.code for r in u.roles]}
            for u in rows]
