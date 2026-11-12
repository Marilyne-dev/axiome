"""Console éditeur : gestion des offres (prix, quotas) et suivi des abonnements / paiements par cabinet.

Réservé au SUPERADMIN (l'éditeur AXIOME). Pages HTML rendues côté serveur, comme le reste de la console.
"""
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.routes_public import _rafraichir
from app.core.database import get_db
from app.core.i18n import t
from app.models.billing import Paiement, Plan
from app.services import billing_service as bs
from app.services.audit_service import journaliser

router = APIRouter(tags=["console_facturation"], include_in_schema=False)

_templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "templates"))
_templates.env.globals["t"] = t


def _fmt(montant: int, devise: str) -> str:
    """Montant stocké en unités mineures : centimes pour l'EUR, unité entière pour le XOF."""
    if devise == "XOF":
        return f"{montant:,}".replace(",", " ") + " FCFA"
    return f"{montant / 100:,.2f}".replace(",", " ").replace(".", ",") + " €"


_templates.env.globals["fmt_montant"] = _fmt


def _garde(request: Request, db: Session):
    try:
        user = get_current_user(request, db)
    except HTTPException:
        return None, RedirectResponse("/login", status_code=302)
    if not user.has_role("SUPERADMIN"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Réservé à l'éditeur AXIOME.")
    return user, None


# ------------------------------------------------------------------ abonnements et paiements
@router.get("/console/abonnements", response_class=HTMLResponse)
def console_abonnements(request: Request, statut: str = "", msg: str = "", db: Session = Depends(get_db)):
    user, redir = _garde(request, db)
    if redir:
        return redir
    lignes = bs.lignes_abonnements(db)
    comptes = {}
    for l in lignes:
        comptes[l["statut"]] = comptes.get(l["statut"], 0) + 1
    if statut:
        lignes = [l for l in lignes if l["statut"] == statut]
    return _templates.TemplateResponse(request, "console_abonnements.html", {
        "lang": user.lang, "user": user, "lignes": lignes, "comptes": comptes, "filtre": statut, "msg": msg,
        "paiements": bs.derniers_paiements(db, 100)})


@router.post("/console/paiements/{reference}/confirmer-virement")
def console_confirmer_virement(reference: str, request: Request, db: Session = Depends(get_db)):
    """À utiliser une fois le virement constaté sur le compte bancaire : active ou prolonge l'abonnement."""
    user, redir = _garde(request, db)
    if redir:
        return redir
    pay = db.query(Paiement).filter_by(reference=reference).first()
    if not pay or pay.fournisseur != "virement" or pay.statut != "en_attente":
        return RedirectResponse("/console/abonnements?msg=" + quote("Paiement introuvable ou déjà clos."), status_code=302)
    pay.fournisseur_ref = "recu"
    db.commit()
    _rafraichir(db, pay)
    journaliser(db, user_id=user.id, action="console.virement_confirme", objet="paiement", detail=reference[:12])
    db.commit()
    return RedirectResponse("/console/abonnements?msg=" + quote("Virement confirmé : abonnement activé."), status_code=302)


# ------------------------------------------------------------------ offres
def _formulaire_plan(nom, description, fonctionnalites, prix_mensuel_eur, prix_annuel_eur, prix_mensuel_xof,
                     prix_annuel_xof, quota_collaborateurs, quota_missions, ordre, is_featured, is_active,
                     appliquer_aux_cabinets):
    return dict(nom=nom, description=description, fonctionnalites=fonctionnalites,
                prix_mensuel_eur=prix_mensuel_eur, prix_annuel_eur=prix_annuel_eur,
                prix_mensuel_xof=prix_mensuel_xof, prix_annuel_xof=prix_annuel_xof,
                quota_collaborateurs=quota_collaborateurs, quota_missions=quota_missions, ordre=ordre,
                is_featured=bool(is_featured), is_active=bool(is_active),
                appliquer_aux_cabinets=bool(appliquer_aux_cabinets))


@router.get("/console/offres", response_class=HTMLResponse)
def console_offres(request: Request, msg: str = "", err: str = "", db: Session = Depends(get_db)):
    user, redir = _garde(request, db)
    if redir:
        return redir
    plans = db.query(Plan).order_by(Plan.ordre, Plan.id).all()
    vues = [{"plan": p, "lignes": "\n".join(json.loads(p.fonctionnalites or "[]")),
             "eur_m": f"{p.prix_mensuel_eur / 100:.2f}", "eur_a": f"{p.prix_annuel_eur / 100:.2f}"} for p in plans]
    return _templates.TemplateResponse(request, "console_offres.html", {
        "lang": user.lang, "user": user, "plans": vues, "msg": msg, "err": err})


@router.post("/console/offres")
def console_offre_creer(
    request: Request, code: str = Form(""), nom: str = Form(""), description: str = Form(""),
    fonctionnalites: str = Form(""), prix_mensuel_eur: str = Form("0"), prix_annuel_eur: str = Form("0"),
    prix_mensuel_xof: str = Form("0"), prix_annuel_xof: str = Form("0"), quota_collaborateurs: str = Form("0"),
    quota_missions: str = Form("0"), ordre: str = Form("0"), is_featured: str = Form(""), is_active: str = Form("on"),
    appliquer_aux_cabinets: str = Form(""), db: Session = Depends(get_db)):
    user, redir = _garde(request, db)
    if redir:
        return redir
    try:
        plan = bs.enregistrer_plan(db, None, code=code, **_formulaire_plan(
            nom, description, fonctionnalites, prix_mensuel_eur, prix_annuel_eur, prix_mensuel_xof, prix_annuel_xof,
            quota_collaborateurs, quota_missions, ordre, is_featured, is_active, False))
    except HTTPException as exc:
        return RedirectResponse("/console/offres?err=" + quote(str(exc.detail)), status_code=302)
    journaliser(db, user_id=user.id, action="console.offre_creee", objet="plan", detail=plan.code)
    db.commit()
    return RedirectResponse("/console/offres?msg=" + quote(f"Offre « {plan.nom} » créée."), status_code=302)


@router.post("/console/offres/{plan_id}")
def console_offre_modifier(
    plan_id: int, request: Request, nom: str = Form(""), description: str = Form(""),
    fonctionnalites: str = Form(""), prix_mensuel_eur: str = Form("0"), prix_annuel_eur: str = Form("0"),
    prix_mensuel_xof: str = Form("0"), prix_annuel_xof: str = Form("0"), quota_collaborateurs: str = Form("0"),
    quota_missions: str = Form("0"), ordre: str = Form("0"), is_featured: str = Form(""), is_active: str = Form(""),
    appliquer_aux_cabinets: str = Form(""), db: Session = Depends(get_db)):
    user, redir = _garde(request, db)
    if redir:
        return redir
    plan = db.get(Plan, plan_id)
    if not plan:
        return RedirectResponse("/console/offres?err=" + quote("Offre introuvable."), status_code=302)
    try:
        bs.enregistrer_plan(db, plan, **_formulaire_plan(
            nom, description, fonctionnalites, prix_mensuel_eur, prix_annuel_eur, prix_mensuel_xof, prix_annuel_xof,
            quota_collaborateurs, quota_missions, ordre, is_featured, is_active, appliquer_aux_cabinets))
    except HTTPException as exc:
        db.rollback()
        return RedirectResponse("/console/offres?err=" + quote(str(exc.detail)), status_code=302)
    journaliser(db, user_id=user.id, action="console.offre_modifiee", objet="plan", detail=plan.code)
    db.commit()
    return RedirectResponse("/console/offres?msg=" + quote(f"Offre « {plan.nom} » enregistrée."), status_code=302)
