"""API publique : offres, inscription d'un cabinet, retour de paiement, notifications des fournisseurs."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.billing import Abonnement, Paiement, Plan
from app.models.user import User
from app.services import billing_service as bs
from app.services import payment_providers as pp

router = APIRouter(tags=["public"])


class SignupIn(BaseModel):
    plan_code: str
    periode: str = "mensuel"
    devise: str = "EUR"
    cabinet_nom: str = Field(min_length=2, max_length=180)
    pays: str = Field(default="France", max_length=80)
    admin_nom: str = Field(min_length=2, max_length=150)
    admin_email: EmailStr
    admin_password: str = Field(min_length=10, max_length=128)


def ouvrir_paiement(db: Session, pay: Paiement, email: str, nom: str) -> str:
    """URL de la page de paiement AXIOME, où le payeur choisit son moyen de paiement."""
    return pp.url_paiement(pay.reference)


@router.get("/public/plans")
def plans(db: Session = Depends(get_db)) -> list[dict]:
    return [bs.plan_public(p) for p in bs.liste_plans(db)]


@router.post("/public/signup", status_code=status.HTTP_201_CREATED)
def signup(data: SignupIn, db: Session = Depends(get_db)) -> dict:
    abo, pay = bs.inscrire(db, plan_code=data.plan_code, periode=data.periode, devise=data.devise,
                           cabinet_nom=data.cabinet_nom, pays=data.pays, admin_nom=data.admin_nom,
                           admin_email=data.admin_email, admin_password=data.admin_password)
    return {"reference": pay.reference, "checkout_url": pp.url_paiement(pay.reference), "montant": pay.montant,
            "devise": pay.devise, "message": ""}


def _paiement(db: Session, reference: str) -> Paiement:
    pay = db.query(Paiement).filter_by(reference=reference).first()
    if not pay:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Paiement introuvable")
    return pay


def _rafraichir(db: Session, pay: Paiement) -> None:
    """Interroge le fournisseur et active l'abonnement si le paiement est confirmé."""
    if pay.statut != "en_attente" or not pay.fournisseur_ref:
        return
    etat = pp.verifier(pay.fournisseur, pay.fournisseur_ref)
    if etat == "paye":
        bs.activer(db, pay)
    elif etat == "echoue":
        pay.statut = "echoue"
        db.commit()


@router.get("/public/paiements/{reference}")
def etat_paiement(reference: str, db: Session = Depends(get_db)) -> dict:
    pay = _paiement(db, reference)
    _rafraichir(db, pay)
    abo = db.get(Abonnement, pay.abonnement_id)
    return {"statut": pay.statut, "abonnement": bs.statut_effectif(abo), "plan": db.get(Plan, pay.plan_id or abo.plan_id).nom,
            "montant": pay.montant, "devise": pay.devise, "periode": pay.periode}


@router.post("/public/paiements/{reference}/confirmer-test")
def confirmer_test(reference: str, db: Session = Depends(get_db)) -> dict:
    """Bouton « Simuler » : uniquement hors production et si PAYMENT_SANDBOX=true. Jamais en production."""
    if not pp.sandbox_actif():
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Indisponible")
    pay = _paiement(db, reference)
    if pay.statut != "en_attente":
        raise HTTPException(status.HTTP_409_CONFLICT, "Ce paiement est déjà clos")
    pay.fournisseur, pay.fournisseur_ref = "test", "confirme"
    db.commit()
    _rafraichir(db, pay)
    return {"statut": pay.statut}


def _paiement_ouvert(db: Session, reference: str) -> tuple[Paiement, Abonnement, Plan]:
    pay = _paiement(db, reference)
    if pay.statut != "en_attente":
        raise HTTPException(status.HTTP_409_CONFLICT, "Ce paiement est déjà clos")
    abo = db.get(Abonnement, pay.abonnement_id)
    return pay, abo, db.get(Plan, pay.plan_id or abo.plan_id)


def _payeur(db: Session, abo: Abonnement) -> tuple[str, str]:
    """E-mail et nom de l'administrateur du cabinet (premier compte créé)."""
    u = db.query(User).filter(User.cabinet_id == abo.cabinet_id).order_by(User.id).first()
    return (u.email, u.nom_complet or u.email) if u else ("", "")


def _libelle(plan: Plan, pay: Paiement) -> str:
    return f"AXIOME — offre {plan.nom} ({pay.periode})"


def _coordonnees_virement(pay: Paiement) -> dict:
    return {"titulaire": settings.virement_titulaire, "banque": settings.virement_banque, "iban": settings.virement_iban,
            "bic": settings.virement_bic, "reference": f"AXIOME-{pay.reference[:10].upper()}",
            "montant": pay.montant, "devise": pay.devise}


@router.get("/public/paiements/{reference}/options")
def options_paiement(reference: str, db: Session = Depends(get_db)) -> dict:
    """Moyens de paiement disponibles pour ce paiement (selon la devise et la configuration)."""
    pay = _paiement(db, reference)
    _rafraichir(db, pay)
    abo = db.get(Abonnement, pay.abonnement_id)
    return {"statut": pay.statut, "plan": db.get(Plan, pay.plan_id or abo.plan_id).nom, "periode": pay.periode,
            "montant": pay.montant, "devise": pay.devise, "methodes": pp.methodes_disponibles(pay.devise),
            "stripe_cle_publique": settings.stripe_publishable_key if pay.devise == "EUR" else "",
            "simulation": pp.sandbox_actif(), "fournisseur": pay.fournisseur}


class MobileMoneyIn(BaseModel):
    operateur: str
    numero: str = Field(min_length=8, max_length=20)


@router.post("/public/paiements/{reference}/stripe")
def payer_stripe(reference: str, db: Session = Depends(get_db)) -> dict:
    pay, abo, plan = _paiement_ouvert(db, reference)
    if pay.devise != "EUR":
        raise HTTPException(422, "Stripe est réservé aux paiements en euros")
    email, _ = _payeur(db, abo)
    try:
        pi, secret = pp.stripe_creer_intention(reference=pay.reference, montant=pay.montant, devise=pay.devise,
                                               libelle=_libelle(plan, pay), email=email)
    except pp.ErreurPaiement as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
    pay.fournisseur, pay.fournisseur_ref = "stripe", pi
    db.commit()
    return {"client_secret": secret, "cle_publique": settings.stripe_publishable_key}


@router.post("/public/paiements/{reference}/mobile-money")
def payer_mobile_money(reference: str, data: MobileMoneyIn, db: Session = Depends(get_db)) -> dict:
    pay, abo, plan = _paiement_ouvert(db, reference)
    if pay.devise != "XOF" or not settings.fedapay_secret_key:
        raise HTTPException(422, "Mobile Money indisponible pour ce paiement")
    email, nom = _payeur(db, abo)
    try:
        tid = pp.fedapay_mobile_money(reference=pay.reference, montant=pay.montant, devise=pay.devise,
                                      libelle=_libelle(plan, pay), email=email, nom=nom,
                                      operateur=data.operateur, numero=data.numero)
    except pp.ErreurPaiement as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
    pay.fournisseur, pay.fournisseur_ref = "fedapay", tid
    db.commit()
    return {"message": "Demande envoyée. Validez le paiement sur votre téléphone (saisie de votre code secret)."}


@router.post("/public/paiements/{reference}/fedapay")
def payer_fedapay(reference: str, db: Session = Depends(get_db)) -> dict:
    pay, abo, plan = _paiement_ouvert(db, reference)
    if pay.devise != "XOF" or not settings.fedapay_secret_key:
        raise HTTPException(422, "FedaPay indisponible pour ce paiement")
    email, nom = _payeur(db, abo)
    try:
        tid, url = pp.fedapay_lien(reference=pay.reference, montant=pay.montant, devise=pay.devise,
                                   libelle=_libelle(plan, pay), email=email, nom=nom)
    except pp.ErreurPaiement as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
    pay.fournisseur, pay.fournisseur_ref = "fedapay", tid
    db.commit()
    return {"url": url}


@router.post("/public/paiements/{reference}/virement")
def payer_virement(reference: str, db: Session = Depends(get_db)) -> dict:
    pay, _abo, _plan = _paiement_ouvert(db, reference)
    if not pp.virement_configure():
        raise HTTPException(422, "Virement indisponible")
    pay.fournisseur, pay.fournisseur_ref = "virement", "attente"
    db.commit()
    return _coordonnees_virement(pay)


@router.post("/admin/paiements/{reference}/confirmer-virement")
def confirmer_virement(reference: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    """Réservé à l'éditeur : à appeler une fois le virement constaté sur le compte bancaire."""
    if not user.has_role("SUPERADMIN"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Réservé à l'éditeur")
    pay = _paiement(db, reference)
    if pay.fournisseur != "virement":
        raise HTTPException(status.HTTP_409_CONFLICT, "Ce paiement n'est pas un virement")
    pay.fournisseur_ref = "recu"
    db.commit()
    _rafraichir(db, pay)
    return {"statut": pay.statut}


async def _notification(request: Request, fournisseur: str, db: Session, ref_fournisseur) -> dict:
    """Le contenu reçu sert uniquement à retrouver le paiement ; l'état réel est relu chez le fournisseur."""
    try:
        ref = ref_fournisseur(await request.json())
    except Exception:       # noqa: BLE001 - corps invalide : on répond OK pour ne pas relancer en boucle
        return {"ok": True}
    pay = db.query(Paiement).filter_by(fournisseur=fournisseur, fournisseur_ref=str(ref)).first() if ref else None
    if pay:
        _rafraichir(db, pay)
    return {"ok": True}


@router.post("/webhooks/stripe", include_in_schema=False)
async def webhook_stripe(request: Request, db: Session = Depends(get_db)) -> dict:
    return await _notification(request, "stripe", db, lambda j: (j.get("data") or {}).get("object", {}).get("id"))


@router.post("/webhooks/fedapay", include_in_schema=False)
async def webhook_fedapay(request: Request, db: Session = Depends(get_db)) -> dict:
    def ref(j: dict):
        o = j.get("entity") or j.get("object") or j.get("v1/transaction") or {}
        return o.get("id") if isinstance(o, dict) else None
    return await _notification(request, "fedapay", db, ref)
