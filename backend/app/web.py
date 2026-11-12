"""Couche web (Jinja2) : espace de travail des missions, rendu côté serveur.

Réutilise les services métier (import, seuils, analyse, Benford) pour afficher
un dossier complet par mission. Authentification par cookie (get_current_user).
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.routes_programme import PROCEDURES_STANDARD, _get_programme
from app.core.cycles_ref import CYCLES, cs_representatif, cycle_pour_cs, libelle_cycle
from app.core.database import get_db
from app.core.i18n import t
from app.core.missions_ref import (
    TYPES_MISSION,
    libelle_categorie,
    types_par_categorie,
)
from app.core.missions_ref import (
    type_mission as _type_mission_def,
)
from app.core.referentiels_contenu import (
    CORRESPONDANCE_NEP_ISA,
    REFERENTIELS_CONTENU,
    contenu_referentiel,
    normes_audit,
)
from app.core.security import hash_password
from app.models.acceptation import Acceptation, LettreMission
from app.models.analyse_tva import LigneTVA
from app.models.audit import AuditLog, Confirmation, Document, RiskItem, Sample, Threshold
from app.models.auth_token import OutboxEmail
from app.models.balance import LigneBalance
from app.models.balance_agee import BalanceAgee
from app.models.cabinet import Bureau, Cabinet
from app.models.cadrage_dsn import LigneCadrageDSN
from app.models.client import Client
from app.models.controle_interne import ControleInterne
from app.models.echantillonnage import SampleItem
from app.models.lcbft import DeclarationSoupcon, DossierLCBFT
from app.models.mission import Cycle, Mission, MissionDiligence
from app.models.planification import AffectationEquipe, Jalon, LigneBudget, PlanMission
from app.models.programme import ProcedureAudit
from app.models.rapprochement import RapprochementBancaire
from app.models.user import Role as _Role
from app.models.user import User as _User
from app.services import (
    controles_service,
    csrd_service,
    document_service,
    editions_service,
    fec_import_service,
    fraude_fec_service,
    fusion_service,
    invitation_service,
    mailer,
    ocr_service,
    tracfin_service,
    veille_service,
    verifications_service,
)
from app.services.analyse_service import analyse_complete
from app.services.analyse_tva_service import cadrage as tva_cadrage
from app.services.analyse_tva_service import initialiser as tva_init
from app.services.audit_service import journaliser
from app.services.balance_agee_service import cadrage as ba_cadrage
from app.services.balance_agee_service import initialiser as ba_init
from app.services.benford_service import analyse_benford, indicateurs_fraude
from app.services.cadrage_dsn_service import cadrage as dsn_cadrage
from app.services.cadrage_dsn_service import initialiser as dsn_init
from app.services.conclusion_service import enregistrer as enregistrer_conclusion
from app.services.conclusion_service import lister as lister_conclusions
from app.services.echantillon_service import taille_attributs, taille_mus
from app.services.import_service import importer_balance
from app.services.lcbft_service import classifier_risque, screening
from app.services.pilotage_service import synthese as pilotage_synthese
from app.services.rapports_service import (
    docx_vers_pdf,
    note_verifications_specifiques,
    rapport_assurance_csrd,
    rapport_commissaire_fusion,
)
from app.services.rapprochement_service import cadrage as rappro_cadrage
from app.services.rapprochement_service import initialiser as rappro_init
from app.services.revue_service import revue_analytique
from app.services.risque_service import heatmap as calc_heatmap
from app.services.risque_service import niveau as niveau_risque
from app.services.risque_service import prioriser

router = APIRouter(tags=["web"])

_templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))
_templates.env.globals["t"] = t


def _user_or_redirect(request: Request, db: Session):
    try:
        return get_current_user(request, db)
    except HTTPException:
        return None


def _missions_visibles(db: Session, user):
    """Missions visibles par l'utilisateur : cloisonnées au cabinet, sauf éditeur."""
    q = db.query(Mission).filter(Mission.is_archived.is_(False))
    if not user.has_role("SUPERADMIN"):
        if not user.cabinet_id:
            return []
        q = q.join(Client, Mission.client_id == Client.id).filter(
            Client.cabinet_id == user.cabinet_id)
    return q.order_by(Mission.id.desc()).all()


def _mission_autorisee(db: Session, user, mission) -> bool:
    """Vrai si l'utilisateur a le droit d'accéder à cette mission (cloisonnement)."""
    if user.has_role("SUPERADMIN"):
        return True
    if not user.cabinet_id:
        return False
    cli = db.get(Client, mission.client_id)
    return bool(cli and cli.cabinet_id == user.cabinet_id)


def _diligences(db: Session, mission):
    """Définition du type + checklist des diligences (créée/synchronisée selon le type)."""
    tdef = _type_mission_def(mission.type_mission)
    rows = (db.query(MissionDiligence).filter_by(mission_id=mission.id)
            .order_by(MissionDiligence.id).all())
    if [d.libelle for d in rows] != tdef["diligences"]:
        for d in rows:
            db.delete(d)
        db.flush()
        for i, lib in enumerate(tdef["diligences"]):
            db.add(MissionDiligence(mission_id=mission.id, code=str(i), libelle=lib, fait=False))
        db.commit()
        rows = (db.query(MissionDiligence).filter_by(mission_id=mission.id)
                .order_by(MissionDiligence.id).all())
    return tdef, rows


@router.get("/missions", response_class=HTMLResponse, include_in_schema=False)
def missions_page(request: Request, db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    missions = _missions_visibles(db, user)
    return _templates.TemplateResponse(request, "missions.html",
                                       {"lang": user.lang, "user": user, "missions": missions})


@router.get("/missions/{mission_id}/vue", response_class=HTMLResponse, include_in_schema=False)
def mission_workspace(mission_id: int, request: Request, db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    mission = db.get(Mission, mission_id)
    if not mission:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mission introuvable")
    if not _mission_autorisee(db, user, mission):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Mission hors de votre périmètre.")

    lignes = db.query(LigneBalance).filter_by(mission_id=mission_id).all()
    seuils = db.query(Threshold).filter_by(mission_id=mission_id).first()
    analyse = analyse_complete(lignes) if lignes else None
    benford = analyse_benford([l.solde_n for l in lignes if l.solde_n]) if lignes else None
    controles = controles_service.controler(lignes) if lignes else None
    seuil_signif = seuils.seuil_signification if seuils else 0.0
    if lignes and seuil_signif:
        revue = revue_analytique(lignes, seuil=seuil_signif)
        variations = [l for l in revue["lignes"] if l["significatif"]]
    else:
        variations = []
    conclusions = lister_conclusions(db, mission_id)
    cycles = [{"code": c, "libelle": libelle_cycle(c),
               "conclusion": conclusions[c].conclusion if c in conclusions else "",
               "anomalie": conclusions[c].anomalie if c in conclusions else False} for c in CYCLES]

    type_def, diligences = _diligences(db, mission)
    return _templates.TemplateResponse(request, "mission.html", {
        "lang": user.lang, "user": user, "mission": mission,
        "nb_lignes": len(lignes), "seuils": seuils, "analyse": analyse,
        "benford": benford, "cycles": cycles, "controles": controles,
        "variations": variations, "seuil_signif": seuil_signif,
        "normes": normes_audit(mission.referentiel),
        "ref_contenu": contenu_referentiel(mission.referentiel),
        "type_def": type_def, "type_categorie_lib": libelle_categorie(type_def["categorie"]),
        "diligences": diligences,
    })



@router.post("/missions/{mission_id}/cycles/{code}/conclusion-web", include_in_schema=False)
def conclusion_web(mission_id: int, code: str, request: Request,
                   conclusion: str = Form(""), anomalie: str = Form(""),
                   db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    if not db.get(Mission, mission_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mission introuvable")
    enregistrer_conclusion(db, mission_id, code, conclusion.strip(), anomalie == "on")
    return RedirectResponse(f"/missions/{mission_id}/vue#cycles", status_code=302)



@router.get("/vue/clients", response_class=HTMLResponse, include_in_schema=False)
def clients_page(request: Request, db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    q = db.query(Client).filter(Client.is_archived.is_(False))
    if user.cabinet_id:
        q = q.filter(Client.cabinet_id == user.cabinet_id)
    from app.core.referentiels_contenu import REFERENTIELS_CONTENU
    return _templates.TemplateResponse(request, "clients.html",
                                       {"lang": user.lang, "user": user, "clients": q.all(),
                                        "types_cat": types_par_categorie(),
                                        "referentiels": list(REFERENTIELS_CONTENU.keys())})


@router.post("/vue/clients", include_in_schema=False)
def client_creer_web(request: Request, raison_sociale: str = Form(...),
                     identifiant_legal: str = Form(""), pays: str = Form("France"),
                     secteur: str = Form(""), db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    if not user.cabinet_id:
        raise HTTPException(status.HTTP_409_CONFLICT, "Utilisateur sans cabinet rattaché.")
    if raison_sociale.strip():
        db.add(Client(cabinet_id=user.cabinet_id, raison_sociale=raison_sociale.strip(),
                      identifiant_legal=identifiant_legal.strip(), pays=pays.strip() or "France",
                      secteur=secteur.strip()))
        db.commit()
    return RedirectResponse("/vue/clients", status_code=302)


@router.post("/vue/missions/creer", include_in_schema=False)
def mission_creer_web(request: Request, client_id: int = Form(...),
                      intitule: str = Form(...), exercice: str = Form(""),
                      type_mission: str = Form("CERT_ANNUELS"),
                      referentiel: str = Form("PCG_FR"), devise: str = Form("EUR"),
                      db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    if not user.cabinet_id:
        raise HTTPException(status.HTTP_409_CONFLICT, "Utilisateur sans cabinet rattaché.")
    client = db.get(Client, client_id)
    if not client or client.cabinet_id != user.cabinet_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Client hors de votre périmètre.")
    cab = db.get(Cabinet, user.cabinet_id)
    if cab and cab.quota_missions and cab.quota_missions > 0:
        nb = (db.query(Mission).join(Client, Mission.client_id == Client.id)
              .filter(Client.cabinet_id == user.cabinet_id).count())
        if nb >= cab.quota_missions:
            return RedirectResponse("/vue/clients?err=quota_missions", status_code=302)
    tcode = type_mission if type_mission in TYPES_MISSION else "CERT_ANNUELS"
    if intitule.strip():
        m = Mission(client_id=client.id, intitule=intitule.strip(),
                    exercice=exercice.strip(), type_mission=tcode,
                    referentiel=referentiel.strip() or "PCG_FR",
                    devise=(devise.strip()[:3] or "EUR").upper(),
                    pays=client.pays or "France")
        db.add(m)
        journaliser(db, user_id=user.id, action="mission.creer", objet="mission",
                    detail=f"{intitule.strip()} [{tcode}]")
        db.commit()
        return RedirectResponse(f"/missions/{m.id}/vue", status_code=302)
    return RedirectResponse("/vue/clients", status_code=302)


@router.post("/missions/{mission_id}/vue/diligence/{did}/toggle", include_in_schema=False)
def diligence_toggle(mission_id: int, did: int, request: Request, db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    mission = _mission_ou_404(db, mission_id)
    if not _mission_autorisee(db, user, mission):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Mission hors de votre périmètre.")
    d = db.get(MissionDiligence, did)
    if d and d.mission_id == mission.id:
        d.fait = not d.fait
        db.commit()
    return RedirectResponse(f"/missions/{mission_id}/vue", status_code=302)


@router.get("/vue/catalogue", include_in_schema=False)
def catalogue_page(request: Request, db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    return _templates.TemplateResponse(request, "catalogue.html", {
        "lang": user.lang, "user": user, "types_cat": types_par_categorie()})


@router.get("/missions/{mission_id}/vue/csrd", include_in_schema=False)
def csrd_page(mission_id: int, request: Request, db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    mission = _mission_ou_404(db, mission_id)
    if not _mission_autorisee(db, user, mission):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Mission hors de votre périmètre.")
    etat = csrd_service.etat(db, mission_id)
    return _templates.TemplateResponse(request, "csrd.html", {
        "lang": user.lang, "user": user, "mission": mission, "etat": etat})


@router.post("/missions/{mission_id}/vue/csrd/materialite/{esrs_code}", include_in_schema=False)
def csrd_materialite_save(mission_id: int, esrs_code: str, request: Request,
                          impact: int = Form(0), financier: int = Form(0),
                          justification: str = Form(""), db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    mission = _mission_ou_404(db, mission_id)
    if not _mission_autorisee(db, user, mission):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Mission hors de votre périmètre.")
    csrd_service.set_materialite(db, mission_id, esrs_code, impact, financier, justification)
    journaliser(db, user_id=user.id, action="csrd.materialite", objet="mission",
                detail=f"{esrs_code} i={impact} f={financier}")
    db.commit()
    return RedirectResponse(f"/missions/{mission_id}/vue/csrd", status_code=302)


@router.post("/missions/{mission_id}/vue/csrd/point/{point_id}/toggle", include_in_schema=False)
def csrd_point_toggle(mission_id: int, point_id: int, request: Request, db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    mission = _mission_ou_404(db, mission_id)
    if not _mission_autorisee(db, user, mission):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Mission hors de votre périmètre.")
    csrd_service.toggle_point(db, mission_id, point_id)
    return RedirectResponse(f"/missions/{mission_id}/vue/csrd", status_code=302)


@router.get("/missions/{mission_id}/vue/csrd/rapport", include_in_schema=False)
def csrd_rapport(mission_id: int, request: Request,
                 format: str = Query("pdf", pattern="^(pdf|docx)$"),
                 db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    mission = _mission_ou_404(db, mission_id)
    if not _mission_autorisee(db, user, mission):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Mission hors de votre périmètre.")
    etat = csrd_service.etat(db, mission_id)
    contenu = rapport_assurance_csrd(mission, etat)
    if format == "pdf":
        contenu = docx_vers_pdf(contenu)
        media = "application/pdf"
    else:
        media = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    editions_service.enregistrer(db, mission_id, "rapport-csrd", format, user.nom_complet or user.email)
    journaliser(db, user_id=user.id, action="csrd.rapport", objet="mission", detail=format)
    db.commit()
    return Response(content=contenu, media_type=media, headers={
        "Content-Disposition": f'attachment; filename="AXIOME_rapport-csrd_{mission_id}.{format}"'})


@router.get("/missions/{mission_id}/vue/verifications", include_in_schema=False)
def verifications_page(mission_id: int, request: Request, db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    mission = _mission_ou_404(db, mission_id)
    if not _mission_autorisee(db, user, mission):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Mission hors de votre périmètre.")
    etat = verifications_service.etat(db, mission_id)
    return _templates.TemplateResponse(request, "verifications.html", {
        "lang": user.lang, "user": user, "mission": mission, "etat": etat})


@router.post("/missions/{mission_id}/vue/verifications/ligne/{code}", include_in_schema=False)
def verifications_ligne(mission_id: int, code: str, request: Request,
                        montant_rapport: str = Form(""), observation: str = Form(""),
                        db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    mission = _mission_ou_404(db, mission_id)
    if not _mission_autorisee(db, user, mission):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Mission hors de votre périmètre.")
    val: float | None = None
    mr = (montant_rapport or "").replace(" ", "").replace(",", ".")
    if mr:
        try:
            val = float(mr)
        except ValueError:
            val = None
    verifications_service.set_ligne(db, mission_id, code, val, observation)
    journaliser(db, user_id=user.id, action="verif.concordance", objet="mission", detail=code)
    db.commit()
    return RedirectResponse(f"/missions/{mission_id}/vue/verifications", status_code=302)


@router.post("/missions/{mission_id}/vue/verifications/point/{code}/toggle", include_in_schema=False)
def verifications_point_toggle(mission_id: int, code: str, request: Request, db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    mission = _mission_ou_404(db, mission_id)
    if not _mission_autorisee(db, user, mission):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Mission hors de votre périmètre.")
    verifications_service.toggle_point(db, mission_id, code)
    return RedirectResponse(f"/missions/{mission_id}/vue/verifications", status_code=302)


@router.get("/missions/{mission_id}/vue/verifications/note", include_in_schema=False)
def verifications_note(mission_id: int, request: Request,
                       format: str = Query("pdf", pattern="^(pdf|docx)$"),
                       db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    mission = _mission_ou_404(db, mission_id)
    if not _mission_autorisee(db, user, mission):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Mission hors de votre périmètre.")
    etat = verifications_service.etat(db, mission_id)
    contenu = note_verifications_specifiques(mission, etat)
    if format == "pdf":
        contenu = docx_vers_pdf(contenu)
        media = "application/pdf"
    else:
        media = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    editions_service.enregistrer(db, mission_id, "note-verifications", format, user.nom_complet or user.email)
    journaliser(db, user_id=user.id, action="verif.note", objet="mission", detail=format)
    db.commit()
    return Response(content=contenu, media_type=media, headers={
        "Content-Disposition": f'attachment; filename="AXIOME_note-verifications_{mission_id}.{format}"'})


@router.get("/missions/{mission_id}/vue/fusion", include_in_schema=False)
def fusion_page(mission_id: int, request: Request, db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    mission = _mission_ou_404(db, mission_id)
    if not _mission_autorisee(db, user, mission):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Mission hors de votre périmètre.")
    etat = fusion_service.etat(db, mission_id)
    return _templates.TemplateResponse(request, "fusion.html", {
        "lang": user.lang, "user": user, "mission": mission, "etat": etat})


def _num_fr(v: str) -> float:
    s = (v or "").replace(" ", "").replace("\u202f", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


@router.post("/missions/{mission_id}/vue/fusion/dossier", include_in_schema=False)
def fusion_dossier(mission_id: int, request: Request,
                   nom_absorbante: str = Form(""), nom_absorbee: str = Form(""),
                   actions_absorbante: str = Form("0"), actions_absorbee: str = Form("0"),
                   valeur_nominale: str = Form("0"), parite_num: str = Form("1"),
                   parite_den: str = Form("1"), db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    mission = _mission_ou_404(db, mission_id)
    if not _mission_autorisee(db, user, mission):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Mission hors de votre périmètre.")
    fusion_service.set_dossier(
        db, mission_id, nom_absorbante=nom_absorbante or "Société absorbante",
        nom_absorbee=nom_absorbee or "Société absorbée",
        actions_absorbante=int(_num_fr(actions_absorbante)),
        actions_absorbee=int(_num_fr(actions_absorbee)),
        valeur_nominale=_num_fr(valeur_nominale),
        parite_num=int(_num_fr(parite_num)) or 1, parite_den=int(_num_fr(parite_den)) or 1)
    journaliser(db, user_id=user.id, action="fusion.dossier", objet="mission", detail=str(mission_id))
    db.commit()
    return RedirectResponse(f"/missions/{mission_id}/vue/fusion", status_code=302)


@router.post("/missions/{mission_id}/vue/fusion/evaluation", include_in_schema=False)
def fusion_evaluation_add(mission_id: int, request: Request,
                          societe: str = Form("A"), methode: str = Form("Autre"),
                          valeur: str = Form("0"), db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    mission = _mission_ou_404(db, mission_id)
    if not _mission_autorisee(db, user, mission):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Mission hors de votre périmètre.")
    fusion_service.ajouter_evaluation(db, mission_id, societe, methode, _num_fr(valeur))
    return RedirectResponse(f"/missions/{mission_id}/vue/fusion", status_code=302)


@router.post("/missions/{mission_id}/vue/fusion/evaluation/{eval_id}/supprimer", include_in_schema=False)
def fusion_evaluation_del(mission_id: int, eval_id: int, request: Request, db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    mission = _mission_ou_404(db, mission_id)
    if not _mission_autorisee(db, user, mission):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Mission hors de votre périmètre.")
    fusion_service.supprimer_evaluation(db, mission_id, eval_id)
    return RedirectResponse(f"/missions/{mission_id}/vue/fusion", status_code=302)


@router.get("/missions/{mission_id}/vue/fusion/rapport", include_in_schema=False)
def fusion_rapport(mission_id: int, request: Request,
                   format: str = Query("pdf", pattern="^(pdf|docx)$"),
                   db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    mission = _mission_ou_404(db, mission_id)
    if not _mission_autorisee(db, user, mission):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Mission hors de votre périmètre.")
    etat = fusion_service.etat(db, mission_id)
    contenu = rapport_commissaire_fusion(mission, etat)
    if format == "pdf":
        contenu = docx_vers_pdf(contenu)
        media = "application/pdf"
    else:
        media = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    editions_service.enregistrer(db, mission_id, "rapport-fusion", format, user.nom_complet or user.email)
    journaliser(db, user_id=user.id, action="fusion.rapport", objet="mission", detail=format)
    db.commit()
    return Response(content=contenu, media_type=media, headers={
        "Content-Disposition": f'attachment; filename="AXIOME_rapport-fusion_{mission_id}.{format}"'})


# ---- Invitations & réinitialisation de mot de passe ----

@router.post("/vue/administration/inviter", include_in_schema=False)
def administration_inviter(request: Request, email: str = Form(...),
                           nom_complet: str = Form(""), role: str = Form("COLLABORATEUR"),
                           db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    if not user.has_role("ADMIN") or not user.cabinet_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Réservé à l'administrateur du cabinet.")
    email = email.strip().lower()
    role_code = role.strip().upper()
    if role_code == "SUPERADMIN":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Rôle non autorisé.")
    if not email or db.query(_User).filter_by(email=email).first():
        return RedirectResponse("/vue/administration?err=email", status_code=302)
    cab = db.get(Cabinet, user.cabinet_id)
    if cab and cab.quota_collaborateurs and cab.quota_collaborateurs > 0:
        nb = db.query(_User).filter_by(cabinet_id=user.cabinet_id, is_archived=False).count()
        if nb >= cab.quota_collaborateurs:
            return RedirectResponse("/vue/administration?err=quota", status_code=302)
    invite = _User(email=email, hashed_password="", nom_complet=nom_complet.strip() or email,
                   is_active=False, lang=user.lang, cabinet_id=user.cabinet_id)
    role_obj = db.query(_Role).filter_by(code=role_code).first()
    if role_obj:
        invite.roles.append(role_obj)
    db.add(invite)
    db.commit()
    lien = invitation_service.creer_lien(db, invite, "invitation", "/activer",
                                         invitation_service.TTL_INVITATION_H)
    corps = ("Bonjour,\n\nVous êtes invité(e) à rejoindre AXIOME. Activez votre compte via ce lien "
             f"(valable 7 jours) :\n{lien}\n")
    mailer.envoyer(db, email, "Invitation à rejoindre AXIOME", corps, lien)
    journaliser(db, user_id=user.id, action="collab.invitation", objet="user", detail=email)
    db.commit()
    from urllib.parse import quote
    return RedirectResponse(f"/vue/administration?lien={quote(lien)}", status_code=302)


@router.get("/activer", response_class=HTMLResponse, include_in_schema=False)
def activer_page(request: Request, token: str = "", db: Session = Depends(get_db)):
    tok, u = invitation_service.valider(db, token, "invitation")
    return _templates.TemplateResponse(request, "activer.html", {
        "lang": "fr", "token": token, "ok": tok is not None,
        "email": u.email if u else ""})


@router.post("/activer", include_in_schema=False)
def activer_submit(request: Request, token: str = Form(""), nom_complet: str = Form(""),
                   password: str = Form(...), db: Session = Depends(get_db)):
    tok, u = invitation_service.valider(db, token, "invitation")
    if not tok or not u:
        return _templates.TemplateResponse(request, "activer.html",
                                           {"lang": "fr", "token": "", "ok": False, "email": ""})
    if len(password) < 8:
        return _templates.TemplateResponse(request, "activer.html", {
            "lang": "fr", "token": token, "ok": True, "email": u.email, "err": "mdp"})
    u.hashed_password = hash_password(password)
    if nom_complet.strip():
        u.nom_complet = nom_complet.strip()
    u.is_active = True
    invitation_service.consommer(db, tok)
    journaliser(db, user_id=u.id, action="compte.active", objet="user", detail=u.email)
    db.commit()
    return RedirectResponse("/login?active=1", status_code=302)


@router.get("/mot-de-passe-oublie", response_class=HTMLResponse, include_in_schema=False)
def reset_demande_page(request: Request, envoye: int = 0):
    return _templates.TemplateResponse(request, "mot_de_passe_oublie.html",
                                       {"lang": "fr", "envoye": bool(envoye)})


@router.post("/mot-de-passe-oublie", include_in_schema=False)
def reset_demande_submit(request: Request, email: str = Form(...), db: Session = Depends(get_db)):
    email = email.strip().lower()
    u = db.query(_User).filter_by(email=email, is_active=True).first()
    if u:
        lien = invitation_service.creer_lien(db, u, "reset", "/reinitialiser",
                                             invitation_service.TTL_RESET_H)
        corps = ("Bonjour,\n\nUne réinitialisation de votre mot de passe AXIOME a été demandée. Ce lien "
                 f"est valable 1 heure :\n{lien}\n\nSi vous n'êtes pas à l'origine de cette demande, "
                 "ignorez ce message.")
        mailer.envoyer(db, email, "Réinitialisation de votre mot de passe AXIOME", corps, lien)
        journaliser(db, user_id=u.id, action="mdp.reset_demande", objet="user", detail=email)
        db.commit()
    return RedirectResponse("/mot-de-passe-oublie?envoye=1", status_code=302)


@router.get("/reinitialiser", response_class=HTMLResponse, include_in_schema=False)
def reset_page(request: Request, token: str = "", db: Session = Depends(get_db)):
    tok, _u = invitation_service.valider(db, token, "reset")
    return _templates.TemplateResponse(request, "reinitialiser.html",
                                       {"lang": "fr", "token": token, "ok": tok is not None})


@router.post("/reinitialiser", include_in_schema=False)
def reset_submit(request: Request, token: str = Form(""), password: str = Form(...),
                 db: Session = Depends(get_db)):
    tok, u = invitation_service.valider(db, token, "reset")
    if not tok or not u:
        return _templates.TemplateResponse(request, "reinitialiser.html",
                                           {"lang": "fr", "token": "", "ok": False})
    if len(password) < 8:
        return _templates.TemplateResponse(request, "reinitialiser.html",
                                           {"lang": "fr", "token": token, "ok": True, "err": "mdp"})
    u.hashed_password = hash_password(password)
    invitation_service.consommer(db, tok)
    journaliser(db, user_id=u.id, action="mdp.reset", objet="user", detail=u.email)
    db.commit()
    return RedirectResponse("/login?reset=1", status_code=302)


@router.get("/console/outbox", response_class=HTMLResponse, include_in_schema=False)
def console_outbox(request: Request, db: Session = Depends(get_db)):
    user, redir = _console_guard(request, db)
    if redir:
        return redir
    messages = (db.query(OutboxEmail)
                .order_by(OutboxEmail.created_at.desc(), OutboxEmail.id.desc()).limit(100).all())
    return _templates.TemplateResponse(request, "outbox.html",
                                       {"lang": user.lang, "user": user, "messages": messages})


@router.post("/console/cabinet/{cid}/quotas", include_in_schema=False)
def console_cabinet_quotas(cid: int, request: Request,
                           quota_collaborateurs: int = Form(0), quota_missions: int = Form(0),
                           db: Session = Depends(get_db)):
    user, redir = _console_guard(request, db)
    if redir:
        return redir
    cab = db.get(Cabinet, cid)
    if cab:
        cab.quota_collaborateurs = max(0, int(quota_collaborateurs))
        cab.quota_missions = max(0, int(quota_missions))
        journaliser(db, user_id=user.id, action="console.quotas", objet="cabinet", detail=str(cid))
        db.commit()
    return RedirectResponse("/console", status_code=302)


@router.get("/console/cabinet/{cid}/journal", response_class=HTMLResponse, include_in_schema=False)
def console_cabinet_journal(cid: int, request: Request, db: Session = Depends(get_db)):
    user, redir = _console_guard(request, db)
    if redir:
        return redir
    cab = db.get(Cabinet, cid)
    if not cab:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cabinet inconnu.")
    membres = db.query(_User).filter_by(cabinet_id=cid).all()
    noms = {u.id: (u.nom_complet or u.email) for u in membres}
    entrees = []
    if noms:
        entrees = (db.query(AuditLog).filter(AuditLog.user_id.in_(list(noms.keys())))
                   .order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).limit(200).all())
    return _templates.TemplateResponse(request, "console_journal.html",
                                       {"lang": user.lang, "user": user, "cabinet": cab,
                                        "entrees": entrees, "noms": noms})


@router.get("/missions/{mission_id}/vue/risques", response_class=HTMLResponse, include_in_schema=False)
def risques_page(mission_id: int, request: Request, db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    mission = db.get(Mission, mission_id)
    if not mission:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mission introuvable")
    risques = db.query(RiskItem).filter_by(mission_id=mission_id).all()
    hc = calc_heatmap(risques)
    ordonnes = [{"r": r, "niveau": niveau_risque(r.score)} for r in prioriser(risques)]
    return _templates.TemplateResponse(request, "risques.html", {
        "lang": user.lang, "user": user, "mission": mission,
        "risques": ordonnes, "heatmap": hc["matrice"], "par_niveau": hc["par_niveau"],
    })


@router.post("/missions/{mission_id}/vue/risques", include_in_schema=False)
def risque_ajouter_web(mission_id: int, request: Request, libelle: str = Form(...),
                       categorie: str = Form("inherent"), probabilite: int = Form(1),
                       impact: int = Form(1), db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    if not db.get(Mission, mission_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mission introuvable")
    if libelle.strip():
        db.add(RiskItem(mission_id=mission_id, libelle=libelle.strip(), categorie=categorie,
                        probabilite=max(1, min(5, probabilite)), impact=max(1, min(5, impact))))
        db.commit()
    return RedirectResponse(f"/missions/{mission_id}/vue/risques", status_code=302)



@router.get("/missions/{mission_id}/vue/cycles", response_class=HTMLResponse, include_in_schema=False)
def cycles_page(mission_id: int, request: Request, db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    mission = db.get(Mission, mission_id)
    if not mission:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mission introuvable")
    return _templates.TemplateResponse(request, "cycles.html", {
        "lang": user.lang, "user": user, "mission": mission, "cycles": mission.cycles})


@router.get("/missions/{mission_id}/vue/cycles/{cycle_id}", response_class=HTMLResponse, include_in_schema=False)
def cycle_detail(mission_id: int, cycle_id: int, request: Request, db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    cycle = db.get(Cycle, cycle_id)
    if not cycle or cycle.mission_id != mission_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cycle introuvable")
    prog = db.query(ProcedureAudit).join(ProcedureAudit.programme).filter_by(cycle_id=cycle_id).all()
    controles = db.query(ControleInterne).filter_by(cycle_id=cycle_id).all()
    faits = sum(1 for p in prog if p.fait)
    return _templates.TemplateResponse(request, "cycle.html", {
        "lang": user.lang, "user": user, "mission": mission_id, "cycle": cycle,
        "procedures": prog, "faits": faits, "controles": controles,
        "modele_dispo": cycle.code.upper() in PROCEDURES_STANDARD})


@router.post("/missions/{mission_id}/vue/cycles/{cycle_id}/programme", include_in_schema=False)
def cycle_generer_programme(mission_id: int, cycle_id: int, request: Request, db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    cycle = db.get(Cycle, cycle_id)
    if not cycle or cycle.mission_id != mission_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cycle introuvable")
    prog = _get_programme(db, cycle_id)
    existantes = {p.reference for p in prog.procedures}
    for ref, lib, assertion in PROCEDURES_STANDARD.get(cycle.code.upper(), []):
        if ref not in existantes:
            db.add(ProcedureAudit(programme_id=prog.id, reference=ref, libelle=lib, assertion=assertion))
    db.commit()
    return RedirectResponse(f"/missions/{mission_id}/vue/cycles/{cycle_id}", status_code=302)


@router.post("/missions/{mission_id}/vue/cycles/{cycle_id}/procedures/{proc_id}/toggle", include_in_schema=False)
def cycle_toggle_procedure(mission_id: int, cycle_id: int, proc_id: int, request: Request,
                           db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    proc = db.get(ProcedureAudit, proc_id)
    if proc:
        proc.fait = not proc.fait
        db.commit()
    return RedirectResponse(f"/missions/{mission_id}/vue/cycles/{cycle_id}", status_code=302)


@router.post("/missions/{mission_id}/vue/cycles/{cycle_id}/controle", include_in_schema=False)
def cycle_ajouter_controle(mission_id: int, cycle_id: int, request: Request,
                           intitule: str = Form(...), composante_coso: str = Form("activites_controle"),
                           conclusion: str = Form("a_tester"), db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    cycle = db.get(Cycle, cycle_id)
    if not cycle or cycle.mission_id != mission_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cycle introuvable")
    if intitule.strip():
        db.add(ControleInterne(cycle_id=cycle_id, intitule=intitule.strip(),
                               composante_coso=composante_coso, conclusion=conclusion))
        db.commit()
    return RedirectResponse(f"/missions/{mission_id}/vue/cycles/{cycle_id}", status_code=302)



def _lcbft_ou_refus(request: Request, db: Session):
    """Accès LCB-FT : correspondant habilité UNIQUEMENT (admin refusé), tout accès tracé."""
    user = _user_or_redirect(request, db)
    if not user:
        return None, RedirectResponse("/login", status_code=302)
    if not user.has_role("CORRESPONDANT_LCBFT"):
        page = _templates.TemplateResponse(request, "lcbft_denied.html",
                                           {"lang": user.lang, "user": user}, status_code=403)
        return None, page
    return user, None


def _tracer_web(db: Session, user, action: str, detail: str, request: Request) -> None:
    journaliser(db, user_id=user.id, action=f"lcbft.web.{action}", objet="lcbft", detail=detail,
                ip=request.client.host if request.client else "")


@router.get("/vue/lcbft", response_class=HTMLResponse, include_in_schema=False)
def lcbft_page(request: Request, db: Session = Depends(get_db)):
    user, refus = _lcbft_ou_refus(request, db)
    if refus:
        return refus
    clients = db.query(Client).filter(Client.is_archived.is_(False)).all()
    dossiers = {d.client_id: d for d in db.query(DossierLCBFT).all()}
    lignes = [{"client": c, "dossier": dossiers.get(c.id)} for c in clients]
    _tracer_web(db, user, "liste", "consultation liste dossiers", request); db.commit()
    return _templates.TemplateResponse(request, "lcbft.html",
                                       {"lang": user.lang, "user": user, "lignes": lignes})


@router.post("/vue/lcbft", include_in_schema=False)
def lcbft_creer(request: Request, client_id: int = Form(...), db: Session = Depends(get_db)):
    user, refus = _lcbft_ou_refus(request, db)
    if refus:
        return refus
    d = db.query(DossierLCBFT).filter_by(client_id=client_id).first()
    if not d:
        d = DossierLCBFT(client_id=client_id); db.add(d); db.flush()
    _tracer_web(db, user, "dossier.upsert", f"client={client_id}", request); db.commit()
    return RedirectResponse(f"/vue/lcbft/{d.id}", status_code=302)


@router.get("/vue/lcbft/{dossier_id}", response_class=HTMLResponse, include_in_schema=False)
def lcbft_dossier(dossier_id: int, request: Request, db: Session = Depends(get_db),
                  screen_nom: str = "", screen_res: str = ""):
    user, refus = _lcbft_ou_refus(request, db)
    if refus:
        return refus
    d = db.get(DossierLCBFT, dossier_id)
    if not d:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dossier introuvable")
    _tracer_web(db, user, "dossier.read", f"dossier={dossier_id}", request); db.commit()
    return _templates.TemplateResponse(request, "lcbft_dossier.html", {
        "lang": user.lang, "user": user, "d": d, "client": db.get(Client, d.client_id),
        "screen_nom": screen_nom, "screen_res": screen_res})


@router.post("/vue/lcbft/{dossier_id}/classification", include_in_schema=False)
def lcbft_classifier(dossier_id: int, request: Request, db: Session = Depends(get_db),
                     pays_a_risque: str = Form(""), activite_especes: str = Form(""),
                     ppe: str = Form(""), structure_complexe: str = Form(""),
                     relation_a_distance: str = Form("")):
    user, refus = _lcbft_ou_refus(request, db)
    if refus:
        return refus
    d = db.get(DossierLCBFT, dossier_id)
    if not d:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dossier introuvable")
    res = classifier_risque(pays_a_risque=pays_a_risque == "on", activite_especes=activite_especes == "on",
                            ppe=ppe == "on", structure_complexe=structure_complexe == "on",
                            relation_a_distance=relation_a_distance == "on")
    d.niveau_risque = res["niveau_risque"]; d.ppe = 1 if ppe == "on" else 0
    _tracer_web(db, user, "classification", f"dossier={dossier_id} niveau={res['niveau_risque']}", request)
    db.commit()
    return RedirectResponse(f"/vue/lcbft/{dossier_id}", status_code=302)


@router.post("/vue/lcbft/{dossier_id}/screening", include_in_schema=False)
def lcbft_screening(dossier_id: int, request: Request, nom: str = Form(...), db: Session = Depends(get_db)):
    user, refus = _lcbft_ou_refus(request, db)
    if refus:
        return refus
    res = screening(nom)
    _tracer_web(db, user, "screening", f"nom={nom} vigilance={res['vigilance']}", request); db.commit()
    return RedirectResponse(f"/vue/lcbft/{dossier_id}?screen_nom={nom}&screen_res={res['vigilance']}",
                            status_code=302)


@router.post("/vue/lcbft/{dossier_id}/declaration", include_in_schema=False)
def lcbft_declaration(dossier_id: int, request: Request, motif: str = Form(...),
                      db: Session = Depends(get_db)):
    user, refus = _lcbft_ou_refus(request, db)
    if refus:
        return refus
    d = db.get(DossierLCBFT, dossier_id)
    if not d:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dossier introuvable")
    if motif.strip():
        db.add(DeclarationSoupcon(dossier_id=dossier_id, redacteur_id=user.id,
                                  reference=f"DS-{dossier_id}-{len(d.declarations)+1}", motif=motif.strip()))
        _tracer_web(db, user, "declaration.create", f"dossier={dossier_id}", request)
        db.commit()
    return RedirectResponse(f"/vue/lcbft/{dossier_id}", status_code=302)



@router.post("/vue/lcbft/{dossier_id}/declaration/{decl_id}/export-tracfin", include_in_schema=False)
def lcbft_export_tracfin(dossier_id: int, decl_id: int, request: Request, db: Session = Depends(get_db)):
    user, refus = _lcbft_ou_refus(request, db)
    if refus:
        return refus
    decl = db.get(DeclarationSoupcon, decl_id)
    if not decl or decl.dossier_id != dossier_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Déclaration introuvable")
    res = tracfin_service.preparer_export(db, decl_id)
    _tracer_web(db, user, "tracfin.export", f"decl={decl_id} ref={res['reference']}", request)
    db.commit()
    return RedirectResponse(f"/vue/lcbft/{dossier_id}?tracfin={res['reference']}", status_code=302)


@router.post("/vue/lcbft/{dossier_id}/declaration/{decl_id}/transmise", include_in_schema=False)
def lcbft_transmise(dossier_id: int, decl_id: int, request: Request, db: Session = Depends(get_db)):
    user, refus = _lcbft_ou_refus(request, db)
    if refus:
        return refus
    decl = db.get(DeclarationSoupcon, decl_id)
    if decl and decl.dossier_id == dossier_id:
        tracfin_service.marquer_transmise(db, decl_id)
        _tracer_web(db, user, "tracfin.transmise", f"decl={decl_id}", request)
        db.commit()
    return RedirectResponse(f"/vue/lcbft/{dossier_id}", status_code=302)


@router.get("/missions/{mission_id}/vue/rapprochement", response_class=HTMLResponse, include_in_schema=False)
def rapprochement_page(mission_id: int, request: Request, db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    mission = db.get(Mission, mission_id)
    if not mission:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mission introuvable")
    rows = db.query(RapprochementBancaire).filter_by(mission_id=mission_id).order_by(
        RapprochementBancaire.compte).all()
    return _templates.TemplateResponse(request, "rapprochement.html", {
        "lang": user.lang, "user": user, "mission": mission,
        "rows": rows, "cadrage": rappro_cadrage(rows) if rows else None})


@router.post("/missions/{mission_id}/vue/rapprochement/init", include_in_schema=False)
def rapprochement_init(mission_id: int, request: Request, db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    if not db.get(Mission, mission_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mission introuvable")
    rappro_init(db, mission_id)
    return RedirectResponse(f"/missions/{mission_id}/vue/rapprochement", status_code=302)


@router.post("/missions/{mission_id}/vue/rapprochement/save", include_in_schema=False)
async def rapprochement_save(mission_id: int, request: Request, db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    if not db.get(Mission, mission_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mission introuvable")
    form = await request.form()
    rows = db.query(RapprochementBancaire).filter_by(mission_id=mission_id).all()
    for r in rows:
        try:
            r.solde_releve = float(str(form.get(f"releve_{r.id}", r.solde_releve)).replace(",", ".") or 0)
        except ValueError:
            pass
        r.valide = form.get(f"valide_{r.id}") == "on"
        r.commentaire = str(form.get(f"comm_{r.id}", "") or "").strip()
    db.commit()
    return RedirectResponse(f"/missions/{mission_id}/vue/rapprochement", status_code=302)



@router.get("/vue/langue/{lang}", include_in_schema=False)
def changer_langue(lang: str, request: Request, db: Session = Depends(get_db)):
    """Bascule la langue de l'utilisateur (FR/EN) et le renvoie d'où il vient."""
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    if lang in ("fr", "en"):
        user.lang = lang
        db.commit()
    retour = request.headers.get("referer") or "/dashboard"
    return RedirectResponse(retour, status_code=302)



@router.get("/vue/referentiels", response_class=HTMLResponse, include_in_schema=False)
def referentiels_page(request: Request, db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    return _templates.TemplateResponse(request, "referentiels.html", {
        "lang": user.lang, "user": user,
        "referentiels": REFERENTIELS_CONTENU, "correspondance": CORRESPONDANCE_NEP_ISA})



def _fraude_context(request, db, mission, user, fec_fraude=None):
    montants = [l.solde_n for l in db.query(LigneBalance).filter_by(mission_id=mission.id).all() if l.solde_n]
    signaux = fraude_fec_service.signaux_res(fec_fraude) if fec_fraude else None
    return {
        "lang": user.lang, "user": user, "mission": mission,
        "benford": analyse_benford(montants) if montants else None,
        "indicateurs": indicateurs_fraude(montants) if montants else None,
        "fec_fraude": fec_fraude,
        "fec_signaux_nb": signaux[0] if signaux else None,
        "fec_signaux_libelles": signaux[1] if signaux else None,
    }


@router.get("/missions/{mission_id}/vue/fraude", response_class=HTMLResponse, include_in_schema=False)
def fraude_page(mission_id: int, request: Request, db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    mission = db.get(Mission, mission_id)
    if not mission:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mission introuvable")
    return _templates.TemplateResponse(request, "fraude.html",
                                       _fraude_context(request, db, mission, user))


@router.post("/missions/{mission_id}/vue/fraude/fec", response_class=HTMLResponse, include_in_schema=False)
async def fraude_fec_analyse(mission_id: int, request: Request, fichier: UploadFile = File(...),
                             seuil: str = Form("10000"), db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    mission = db.get(Mission, mission_id)
    if not mission:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mission introuvable")
    brut = await fichier.read()
    try:
        contenu = brut.decode("utf-8")
    except UnicodeDecodeError:
        contenu = brut.decode("latin-1", errors="replace")
    try:
        seuil_val = float(str(seuil).replace(",", ".")) or 10000.0
    except ValueError:
        seuil_val = 10000.0
    cloture = getattr(mission, "date_cloture", None)
    fec_fraude = fraude_fec_service.analyser_fec(contenu, cloture=cloture, seuil_structuration=seuil_val)
    fraude_fec_service.enregistrer(db, mission_id, fec_fraude, fichier=fichier.filename or "")
    journaliser(db, user_id=user.id, action="fraude.fec", objet="mission",
                detail=f"{fec_fraude['n']} écritures")
    db.commit()
    return _templates.TemplateResponse(request, "fraude.html",
                                       _fraude_context(request, db, mission, user, fec_fraude=fec_fraude))



_BA_CYCLES = {"clients": ("CLIENTS", "Clients"), "fournisseurs": ("FOURNISSEURS", "Fournisseurs")}


@router.get("/missions/{mission_id}/vue/balance-agee/{cycle}", response_class=HTMLResponse, include_in_schema=False)
def balance_agee_page(mission_id: int, cycle: str, request: Request, db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    if cycle not in _BA_CYCLES or not db.get(Mission, mission_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ressource introuvable")
    code, libelle = _BA_CYCLES[cycle]
    rows = db.query(BalanceAgee).filter_by(mission_id=mission_id, cycle=code).order_by(
        BalanceAgee.compte).all()
    return _templates.TemplateResponse(request, "balance_agee.html", {
        "lang": user.lang, "user": user, "mission": mission_id, "cycle": cycle,
        "libelle": libelle, "rows": rows, "cadrage": ba_cadrage(rows) if rows else None})


@router.post("/missions/{mission_id}/vue/balance-agee/{cycle}/init", include_in_schema=False)
def balance_agee_init(mission_id: int, cycle: str, request: Request, db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    if cycle not in _BA_CYCLES or not db.get(Mission, mission_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ressource introuvable")
    ba_init(db, mission_id, _BA_CYCLES[cycle][0])
    return RedirectResponse(f"/missions/{mission_id}/vue/balance-agee/{cycle}", status_code=302)


@router.post("/missions/{mission_id}/vue/balance-agee/{cycle}/save", include_in_schema=False)
async def balance_agee_save(mission_id: int, cycle: str, request: Request, db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    if cycle not in _BA_CYCLES or not db.get(Mission, mission_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ressource introuvable")
    form = await request.form()

    def num(champ: str, defaut: float) -> float:
        try:
            return float(str(form.get(champ, defaut)).replace(",", ".") or 0)
        except ValueError:
            return defaut

    rows = db.query(BalanceAgee).filter_by(mission_id=mission_id, cycle=_BA_CYCLES[cycle][0]).all()
    for r in rows:
        r.non_echu = num(f"non_echu_{r.id}", r.non_echu)
        r.echu_30 = num(f"e30_{r.id}", r.echu_30)
        r.echu_60 = num(f"e60_{r.id}", r.echu_60)
        r.echu_90 = num(f"e90_{r.id}", r.echu_90)
        r.echu_plus = num(f"eplus_{r.id}", r.echu_plus)
        r.commentaire = str(form.get(f"comm_{r.id}", "") or "").strip()
    db.commit()
    return RedirectResponse(f"/missions/{mission_id}/vue/balance-agee/{cycle}", status_code=302)



@router.get("/vue/pilotage", response_class=HTMLResponse, include_in_schema=False)
def pilotage_page(request: Request, db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    return _templates.TemplateResponse(request, "pilotage.html", {
        "lang": user.lang, "user": user,
        # Cloisonnement : cabinet de l'utilisateur (0 = aucun cabinet -> rien), éditeur = tout.
        "s": pilotage_synthese(db, None if user.has_role("SUPERADMIN") else (user.cabinet_id or 0))})


# ------------------------------------------------------------------ Cadrage DSN
@router.get("/missions/{mission_id}/vue/cadrage-dsn", response_class=HTMLResponse, include_in_schema=False)
def cadrage_dsn_page(mission_id: int, request: Request, db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    mission = db.get(Mission, mission_id)
    if not mission:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mission introuvable")
    rows = db.query(LigneCadrageDSN).filter_by(mission_id=mission_id).order_by(
        LigneCadrageDSN.compte).all()
    return _templates.TemplateResponse(request, "cadrage_dsn.html", {
        "lang": user.lang, "user": user, "mission": mission, "rows": rows,
        "cadrage": dsn_cadrage(rows) if rows else None})


@router.post("/missions/{mission_id}/vue/cadrage-dsn/init", include_in_schema=False)
def cadrage_dsn_init(mission_id: int, request: Request, db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    if not db.get(Mission, mission_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mission introuvable")
    dsn_init(db, mission_id)
    return RedirectResponse(f"/missions/{mission_id}/vue/cadrage-dsn", status_code=302)


@router.post("/missions/{mission_id}/vue/cadrage-dsn/save", include_in_schema=False)
async def cadrage_dsn_save(mission_id: int, request: Request, db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    if not db.get(Mission, mission_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mission introuvable")
    form = await request.form()

    def _num(cle: str, defaut: float) -> float:
        try:
            return float(str(form.get(cle, defaut)).replace(",", ".") or 0)
        except ValueError:
            return defaut

    for r in db.query(LigneCadrageDSN).filter_by(mission_id=mission_id).all():
        r.montant_dsn = _num(f"dsn_{r.id}", r.montant_dsn)
        r.commentaire = str(form.get(f"comm_{r.id}", "") or "").strip()
    db.commit()
    return RedirectResponse(f"/missions/{mission_id}/vue/cadrage-dsn", status_code=302)


# ------------------------------------------------------------------ Analyse TVA
@router.get("/missions/{mission_id}/vue/analyse-tva", response_class=HTMLResponse, include_in_schema=False)
def analyse_tva_page(mission_id: int, request: Request, db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    mission = db.get(Mission, mission_id)
    if not mission:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mission introuvable")
    rows = db.query(LigneTVA).filter_by(mission_id=mission_id).order_by(LigneTVA.id).all()
    return _templates.TemplateResponse(request, "analyse_tva.html", {
        "lang": user.lang, "user": user, "mission": mission, "rows": rows,
        "cadrage": tva_cadrage(rows) if rows else None})


@router.post("/missions/{mission_id}/vue/analyse-tva/init", include_in_schema=False)
def analyse_tva_init(mission_id: int, request: Request, db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    if not db.get(Mission, mission_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mission introuvable")
    tva_init(db, mission_id)
    return RedirectResponse(f"/missions/{mission_id}/vue/analyse-tva", status_code=302)


@router.post("/missions/{mission_id}/vue/analyse-tva/save", include_in_schema=False)
async def analyse_tva_save(mission_id: int, request: Request, db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    if not db.get(Mission, mission_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mission introuvable")
    form = await request.form()

    def _num(cle: str, defaut: float) -> float:
        try:
            return float(str(form.get(cle, defaut)).replace(",", ".") or 0)
        except ValueError:
            return defaut

    for r in db.query(LigneTVA).filter_by(mission_id=mission_id).all():
        r.base_ht = _num(f"base_{r.id}", r.base_ht)
        taux = _num(f"taux_{r.id}", r.taux)
        r.taux = taux / 100 if taux > 1 else taux   # accepte 20 ou 0.20
        r.tva_comptabilisee = _num(f"tvac_{r.id}", r.tva_comptabilisee)
        r.commentaire = str(form.get(f"comm_{r.id}", "") or "").strip()
    db.commit()
    return RedirectResponse(f"/missions/{mission_id}/vue/analyse-tva", status_code=302)


def _parse_date(v: str | None):
    try:
        return date.fromisoformat(v) if v else None
    except (ValueError, TypeError):
        return None


def _mission_ou_404(db: Session, mission_id: int) -> Mission:
    m = db.get(Mission, mission_id)
    if not m:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mission introuvable")
    return m


# =========================================================== Acceptation (Module 1)
def _get_or_create_acceptation(db: Session, mission_id: int) -> Acceptation:
    acc = db.query(Acceptation).filter_by(mission_id=mission_id).first()
    if not acc:
        acc = Acceptation(mission_id=mission_id)
        db.add(acc); db.commit(); db.refresh(acc)
    return acc


@router.get("/missions/{mission_id}/vue/acceptation", response_class=HTMLResponse, include_in_schema=False)
def acceptation_page(mission_id: int, request: Request, db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    mission = _mission_ou_404(db, mission_id)
    acc = _get_or_create_acceptation(db, mission_id)
    lettre = db.query(LettreMission).filter_by(acceptation_id=acc.id).first()
    return _templates.TemplateResponse(request, "acceptation.html", {
        "lang": user.lang, "user": user, "mission": mission, "acc": acc, "lettre": lettre,
        "err": request.query_params.get("err")})


@router.post("/missions/{mission_id}/vue/acceptation/save", include_in_schema=False)
async def acceptation_save(mission_id: int, request: Request, db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    _mission_ou_404(db, mission_id)
    form = await request.form()
    acc = _get_or_create_acceptation(db, mission_id)
    acc.independance_ok = "independance_ok" in form
    acc.conflit_interet = "conflit_interet" in form
    acc.kyc_ok = "kyc_ok" in form
    acc.continuite_exploitation_ok = "continuite_exploitation_ok" in form
    acc.niveau_risque_global = str(form.get("niveau_risque_global", "standard"))
    db.commit()
    return RedirectResponse(f"/missions/{mission_id}/vue/acceptation", status_code=302)


@router.post("/missions/{mission_id}/vue/acceptation/decision", include_in_schema=False)
async def acceptation_decision(mission_id: int, request: Request, db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    mission = _mission_ou_404(db, mission_id)
    form = await request.form()
    decision = str(form.get("decision", ""))
    if decision not in {"acceptee", "refusee"}:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Décision invalide")
    acc = _get_or_create_acceptation(db, mission_id)
    if decision == "acceptee" and acc.conflit_interet:
        return RedirectResponse(f"/missions/{mission_id}/vue/acceptation?err=conflit", status_code=302)
    acc.decision = decision
    acc.motivation = str(form.get("motivation", "") or "").strip()
    acc.decideur_id = user.id
    mission.statut = "planification" if decision == "acceptee" else "refusee"
    journaliser(db, user_id=user.id, action=f"acceptation.{decision}", objet="mission", detail=str(mission_id))
    db.commit()
    return RedirectResponse(f"/missions/{mission_id}/vue/acceptation", status_code=302)


@router.post("/missions/{mission_id}/vue/acceptation/lettre", include_in_schema=False)
def acceptation_lettre(mission_id: int, request: Request, db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    mission = _mission_ou_404(db, mission_id)
    acc = _get_or_create_acceptation(db, mission_id)
    if acc.decision != "acceptee":
        return RedirectResponse(f"/missions/{mission_id}/vue/acceptation?err=lettre", status_code=302)
    corps = (
        f"Lettre de mission — {mission.intitule}\n"
        f"Référentiel : {mission.referentiel} · Pays : {mission.pays} · Devise : {mission.devise}\n"
        f"Exercice : {mission.exercice}\n\n"
        "Objet : mission de commissariat aux comptes conformément aux normes applicables (NEP 210)."
    )
    lettre = db.query(LettreMission).filter_by(acceptation_id=acc.id).first()
    if not lettre:
        lettre = LettreMission(acceptation_id=acc.id, reference=f"LM-{mission_id}", corps=corps, statut="brouillon")
        db.add(lettre)
    else:
        lettre.corps = corps
    journaliser(db, user_id=user.id, action="lettre_mission.generer", objet="mission", detail=str(mission_id))
    db.commit()
    return RedirectResponse(f"/missions/{mission_id}/vue/acceptation", status_code=302)


# ========================================================== Planification (Module 3)
def _get_or_create_plan(db: Session, mission_id: int) -> PlanMission:
    plan = db.query(PlanMission).filter_by(mission_id=mission_id).first()
    if not plan:
        plan = PlanMission(mission_id=mission_id)
        db.add(plan); db.commit(); db.refresh(plan)
    return plan


@router.get("/missions/{mission_id}/vue/planification", response_class=HTMLResponse, include_in_schema=False)
def planification_page(mission_id: int, request: Request, db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    mission = _mission_ou_404(db, mission_id)
    plan = _get_or_create_plan(db, mission_id)
    equipe_dispo = db.query(_User).order_by(_User.nom_complet).all()
    total_budget = round(sum(b.montant for b in plan.budget), 2)
    return _templates.TemplateResponse(request, "planification.html", {
        "lang": user.lang, "user": user, "mission": mission, "plan": plan,
        "equipe_dispo": equipe_dispo, "total_budget": total_budget})


@router.post("/missions/{mission_id}/vue/planification/save", include_in_schema=False)
async def planification_save(mission_id: int, request: Request, db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    _mission_ou_404(db, mission_id)
    form = await request.form()
    plan = _get_or_create_plan(db, mission_id)
    plan.date_debut = _parse_date(str(form.get("date_debut", "")))
    plan.date_fin = _parse_date(str(form.get("date_fin", "")))
    plan.approche = str(form.get("approche", "") or "").strip()
    try:
        plan.honoraires = float(str(form.get("honoraires", 0)).replace(",", ".") or 0)
    except ValueError:
        pass
    db.commit()
    return RedirectResponse(f"/missions/{mission_id}/vue/planification", status_code=302)


@router.post("/missions/{mission_id}/vue/planification/jalon", include_in_schema=False)
async def planification_jalon(mission_id: int, request: Request, db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    _mission_ou_404(db, mission_id)
    form = await request.form()
    plan = _get_or_create_plan(db, mission_id)
    libelle = str(form.get("libelle", "") or "").strip()
    if libelle:
        db.add(Jalon(plan_id=plan.id, libelle=libelle,
                     echeance=_parse_date(str(form.get("echeance", "")))))
        db.commit()
    return RedirectResponse(f"/missions/{mission_id}/vue/planification", status_code=302)


@router.post("/missions/{mission_id}/vue/planification/budget", include_in_schema=False)
async def planification_budget(mission_id: int, request: Request, db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    mission = _mission_ou_404(db, mission_id)
    form = await request.form()
    plan = _get_or_create_plan(db, mission_id)
    poste = str(form.get("poste", "") or "").strip()
    if poste:
        try:
            montant = float(str(form.get("montant", 0)).replace(",", ".") or 0)
        except ValueError:
            montant = 0.0
        db.add(LigneBudget(plan_id=plan.id, poste=poste, montant=montant, devise=mission.devise))
        db.commit()
    return RedirectResponse(f"/missions/{mission_id}/vue/planification", status_code=302)


@router.post("/missions/{mission_id}/vue/planification/equipe", include_in_schema=False)
async def planification_equipe(mission_id: int, request: Request, db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    _mission_ou_404(db, mission_id)
    form = await request.form()
    plan = _get_or_create_plan(db, mission_id)
    try:
        uid = int(str(form.get("user_id", 0)))
    except ValueError:
        uid = 0
    if uid and db.get(_User, uid):
        try:
            heures = float(str(form.get("heures_estimees", 0)).replace(",", ".") or 0)
        except ValueError:
            heures = 0.0
        db.add(AffectationEquipe(plan_id=plan.id, user_id=uid,
                                 role_mission=str(form.get("role_mission", "collaborateur")),
                                 heures_estimees=heures))
        db.commit()
    return RedirectResponse(f"/missions/{mission_id}/vue/planification", status_code=302)


# ========================================================= Échantillonnage (Module 11)
@router.get("/missions/{mission_id}/vue/echantillonnage", response_class=HTMLResponse, include_in_schema=False)
def echantillonnage_page(mission_id: int, request: Request, db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    mission = _mission_ou_404(db, mission_id)
    blocs = []
    for cy in db.query(Cycle).filter_by(mission_id=mission_id).order_by(Cycle.code).all():
        samples = []
        for s in db.query(Sample).filter_by(cycle_id=cy.id).all():
            items = db.query(SampleItem).filter_by(sample_id=s.id).all()
            samples.append({"s": s, "items": items})
        blocs.append({"cycle": cy, "samples": samples})
    return _templates.TemplateResponse(request, "echantillonnage.html", {
        "lang": user.lang, "user": user, "mission": mission, "blocs": blocs})


@router.post("/missions/{mission_id}/vue/echantillonnage/cycle/{cycle_id}/sample", include_in_schema=False)
async def echantillonnage_sample(mission_id: int, cycle_id: int, request: Request, db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    _mission_ou_404(db, mission_id)
    cy = db.get(Cycle, cycle_id)
    if not cy or cy.mission_id != mission_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cycle introuvable")
    form = await request.form()
    methode = str(form.get("methode", "aleatoire"))

    def _f(cle: str, defaut: float = 0.0) -> float:
        try:
            return float(str(form.get(cle, defaut)).replace(",", ".") or 0)
        except ValueError:
            return defaut

    if methode == "mus":
        taille = taille_mus(_f("valeur_population"), _f("seuil_tolerable"), _f("confiance", 0.95))
    elif methode == "attributs":
        taille = taille_attributs(_f("taux_tolerable", 0.05), _f("confiance", 0.95))
    else:
        taille = int(_f("taille"))
    db.add(Sample(cycle_id=cycle_id, methode=methode, taille=taille))
    journaliser(db, user_id=user.id, action="echantillon.create", objet="cycle", detail=methode)
    db.commit()
    return RedirectResponse(f"/missions/{mission_id}/vue/echantillonnage", status_code=302)


@router.post("/missions/{mission_id}/vue/echantillonnage/sample/{sample_id}/item", include_in_schema=False)
async def echantillonnage_item(mission_id: int, sample_id: int, request: Request, db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    mission = _mission_ou_404(db, mission_id)
    s = db.get(Sample, sample_id)
    if not s:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Échantillon introuvable")
    form = await request.form()
    ref = str(form.get("reference_piece", "") or "").strip()
    if ref:
        try:
            montant = float(str(form.get("montant", 0)).replace(",", ".") or 0)
        except ValueError:
            montant = 0.0
        db.add(SampleItem(sample_id=sample_id, reference_piece=ref, montant=montant,
                          devise=mission.devise, conclusion="a_tester"))
        db.commit()
    return RedirectResponse(f"/missions/{mission_id}/vue/echantillonnage", status_code=302)


@router.post("/missions/{mission_id}/vue/echantillonnage/item/{item_id}/conclusion", include_in_schema=False)
async def echantillonnage_conclusion(mission_id: int, item_id: int, request: Request, db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    _mission_ou_404(db, mission_id)
    item = db.get(SampleItem, item_id)
    if item:
        form = await request.form()
        item.conclusion = str(form.get("conclusion", "a_tester"))
        db.commit()
    return RedirectResponse(f"/missions/{mission_id}/vue/echantillonnage", status_code=302)


# ========================================================= Confirmations (Module 12)
@router.get("/missions/{mission_id}/vue/confirmations", response_class=HTMLResponse, include_in_schema=False)
def confirmations_page(mission_id: int, request: Request, db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    mission = _mission_ou_404(db, mission_id)
    confs = db.query(Confirmation).filter_by(mission_id=mission_id).order_by(Confirmation.id).all()
    return _templates.TemplateResponse(request, "confirmations.html", {
        "lang": user.lang, "user": user, "mission": mission, "confs": confs})


@router.post("/missions/{mission_id}/vue/confirmations/add", include_in_schema=False)
async def confirmations_add(mission_id: int, request: Request, db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    _mission_ou_404(db, mission_id)
    form = await request.form()
    tiers = str(form.get("tiers", "") or "").strip()
    if tiers:
        db.add(Confirmation(mission_id=mission_id, tiers=tiers,
                            type_tiers=str(form.get("type_tiers", "banque")), statut="envoyee"))
        journaliser(db, user_id=user.id, action="confirmation.create", objet="mission", detail=tiers)
        db.commit()
    return RedirectResponse(f"/missions/{mission_id}/vue/confirmations", status_code=302)


@router.post("/missions/{mission_id}/vue/confirmations/{conf_id}/statut", include_in_schema=False)
async def confirmations_statut(mission_id: int, conf_id: int, request: Request, db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    _mission_ou_404(db, mission_id)
    conf = db.get(Confirmation, conf_id)
    if conf and conf.mission_id == mission_id:
        form = await request.form()
        conf.statut = str(form.get("statut", "envoyee"))
        db.commit()
    return RedirectResponse(f"/missions/{mission_id}/vue/confirmations", status_code=302)


# ================================================================ GED (documents)
@router.get("/missions/{mission_id}/vue/documents", response_class=HTMLResponse, include_in_schema=False)
def documents_page(mission_id: int, request: Request, db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    mission = _mission_ou_404(db, mission_id)
    cycle = request.query_params.get("cycle") or None
    q = (request.query_params.get("q") or "").strip()
    docs = document_service.lister(db, mission_id, cycle)
    if q:
        cible = q.lower()
        docs = [d for d in docs if cible in (d.texte_extrait or "").lower()
                or cible in (d.nom or "").lower()]
    return _templates.TemplateResponse(request, "documents.html", {
        "lang": user.lang, "user": user, "mission": mission, "docs": docs,
        "cycle": cycle or "", "q": q, "ocr_dispo": ocr_service.moteur_ocr_disponible(),
        "err": request.query_params.get("err")})


@router.get("/missions/{mission_id}/vue/editions/export.csv", include_in_schema=False)
def editions_export_csv(mission_id: int, request: Request, db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    _mission_ou_404(db, mission_id)
    contenu = editions_service.exporter_csv(db, mission_id)
    return Response(
        content="\ufeff" + contenu,  # BOM UTF-8 pour Excel
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="journal_editions_M{mission_id}.csv"'},
    )


@router.get("/vue/administration", include_in_schema=False)
def administration_page(request: Request, lien: str = "", err: str = "", db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    if not user.has_role("ADMIN"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Réservé à l'administrateur.")
    cabinet = db.get(Cabinet, user.cabinet_id) if user.cabinet_id else None
    bureaux = (db.query(Bureau).filter_by(cabinet_id=cabinet.id).order_by(Bureau.nom).all()
               if cabinet else [])
    from app.core.referentiels_contenu import REFERENTIELS_CONTENU
    referentiels = list(REFERENTIELS_CONTENU.keys())
    # Collaborateurs du cabinet + rôles assignables (jamais SUPERADMIN).
    collaborateurs = (db.query(_User).filter_by(cabinet_id=cabinet.id).order_by(_User.nom_complet).all()
                      if cabinet else [])
    roles_assignables = (db.query(_Role).filter(_Role.code != "SUPERADMIN")
                         .order_by(_Role.libelle).all())
    return _templates.TemplateResponse(request, "administration.html", {
        "lang": user.lang, "user": user, "cabinet": cabinet,
        "bureaux": bureaux, "referentiels": referentiels, "lien_invitation": lien, "err": err,
        "collaborateurs": collaborateurs, "roles_assignables": roles_assignables})


@router.post("/vue/administration/cabinet", include_in_schema=False)
async def administration_cabinet_save(request: Request, nom: str = Form(...),
                                      pays: str = Form("France"), devise_defaut: str = Form("EUR"),
                                      referentiel_defaut: str = Form("PCG_FR"),
                                      db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    if not user.has_role("ADMIN") or not user.cabinet_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Réservé à l'administrateur.")
    cabinet = db.get(Cabinet, user.cabinet_id)
    if cabinet:
        cabinet.nom = nom.strip() or cabinet.nom
        cabinet.pays = pays.strip() or cabinet.pays
        cabinet.devise_defaut = (devise_defaut.strip()[:3] or cabinet.devise_defaut).upper()
        cabinet.referentiel_defaut = referentiel_defaut.strip() or cabinet.referentiel_defaut
        journaliser(db, user_id=user.id, action="cabinet.maj", objet="cabinet", detail=cabinet.nom)
        db.commit()
    return RedirectResponse("/vue/administration", status_code=302)


@router.post("/vue/administration/bureau", include_in_schema=False)
async def administration_bureau_add(request: Request, nom: str = Form(...),
                                    ville: str = Form(""), pays: str = Form("France"),
                                    db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    if not user.has_role("ADMIN") or not user.cabinet_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Réservé à l'administrateur.")
    if nom.strip():
        db.add(Bureau(cabinet_id=user.cabinet_id, nom=nom.strip(),
                      ville=ville.strip(), pays=pays.strip() or "France"))
        journaliser(db, user_id=user.id, action="bureau.creer", objet="bureau", detail=nom.strip())
        db.commit()
    return RedirectResponse("/vue/administration", status_code=302)


@router.post("/vue/administration/bureau/{bureau_id}/delete", include_in_schema=False)
async def administration_bureau_delete(bureau_id: int, request: Request, db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    if not user.has_role("ADMIN") or not user.cabinet_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Réservé à l'administrateur.")
    bureau = db.get(Bureau, bureau_id)
    if bureau and bureau.cabinet_id == user.cabinet_id:
        db.delete(bureau)
        journaliser(db, user_id=user.id, action="bureau.supprimer", objet="bureau", detail=bureau.nom)
        db.commit()
    return RedirectResponse("/vue/administration", status_code=302)


# ---- CAC : gestion des collaborateurs du cabinet ----
@router.post("/vue/administration/collaborateur", include_in_schema=False)
async def administration_collaborateur_add(
        request: Request, email: str = Form(...), nom_complet: str = Form(""),
        role: str = Form("COLLABORATEUR"), password: str = Form(...),
        db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    if not user.has_role("ADMIN") or not user.cabinet_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Réservé à l'administrateur du cabinet.")
    email = email.strip().lower()
    role_code = role.strip().upper()
    if role_code == "SUPERADMIN":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Rôle non autorisé.")
    if not email or db.query(_User).filter_by(email=email).first():
        return RedirectResponse("/vue/administration?err=email", status_code=302)
    if len(password) < 8:
        return RedirectResponse("/vue/administration?err=mdp", status_code=302)
    cab = db.get(Cabinet, user.cabinet_id)
    if cab and cab.quota_collaborateurs and cab.quota_collaborateurs > 0:
        nb = db.query(_User).filter_by(cabinet_id=user.cabinet_id, is_archived=False).count()
        if nb >= cab.quota_collaborateurs:
            return RedirectResponse("/vue/administration?err=quota", status_code=302)
    nouveau = _User(email=email, hashed_password=hash_password(password),
                    nom_complet=nom_complet.strip() or email, is_active=True,
                    lang=user.lang, cabinet_id=user.cabinet_id)
    role_obj = db.query(_Role).filter_by(code=role_code).first()
    if role_obj:
        nouveau.roles.append(role_obj)
    db.add(nouveau)
    journaliser(db, user_id=user.id, action="collaborateur.creer", objet="user", detail=email)
    db.commit()
    return RedirectResponse("/vue/administration", status_code=302)


@router.post("/vue/administration/collaborateur/{uid}/toggle", include_in_schema=False)
async def administration_collaborateur_toggle(uid: int, request: Request, db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    if not user.has_role("ADMIN") or not user.cabinet_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Réservé à l'administrateur du cabinet.")
    cible = db.get(_User, uid)
    if cible and cible.cabinet_id == user.cabinet_id and cible.id != user.id:
        cible.is_active = not cible.is_active
        etat = "actif" if cible.is_active else "inactif"
        journaliser(db, user_id=user.id, action="collaborateur.toggle", objet="user",
                    detail=f"{cible.email}:{etat}")
        db.commit()
    return RedirectResponse("/vue/administration", status_code=302)


# ---- Console éditeur (SUPERADMIN) : supervision de tous les cabinets ----
def _console_guard(request: Request, db: Session):
    user = _user_or_redirect(request, db)
    if not user:
        return None, RedirectResponse("/login", status_code=302)
    if not user.has_role("SUPERADMIN"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Réservé à l'éditeur AXIOME.")
    return user, None


@router.get("/console", include_in_schema=False)
def console_page(request: Request, db: Session = Depends(get_db)):
    user, redir = _console_guard(request, db)
    if redir:
        return redir
    cabinets = db.query(Cabinet).order_by(Cabinet.nom).all()
    lignes = []
    for c in cabinets:
        nb_users = db.query(_User).filter_by(cabinet_id=c.id).count()
        nb_clients = db.query(Client).filter_by(cabinet_id=c.id).count()
        nb_missions = (db.query(Mission).join(Client, Mission.client_id == Client.id)
                       .filter(Client.cabinet_id == c.id).count())
        lignes.append({"cabinet": c, "users": nb_users, "clients": nb_clients,
                       "missions": nb_missions, "suspendu": c.is_archived,
                       "quota_collaborateurs": c.quota_collaborateurs,
                       "quota_missions": c.quota_missions})
    stats = {
        "cabinets": len(cabinets),
        "cabinets_actifs": sum(1 for c in cabinets if not c.is_archived),
        "users": db.query(_User).count(),
        "clients": db.query(Client).count(),
        "missions": db.query(Mission).count(),
    }
    from app.core.referentiels_contenu import REFERENTIELS_CONTENU
    referentiels = list(REFERENTIELS_CONTENU.keys())
    return _templates.TemplateResponse(request, "console.html", {
        "lang": user.lang, "user": user, "lignes": lignes, "stats": stats,
        "referentiels": referentiels})


@router.post("/console/cabinet", include_in_schema=False)
async def console_cabinet_create(
        request: Request, nom: str = Form(...), pays: str = Form("France"),
        referentiel_defaut: str = Form("PCG_FR"), devise_defaut: str = Form("EUR"),
        cac_email: str = Form(...), cac_nom: str = Form(""), cac_password: str = Form(...),
        db: Session = Depends(get_db)):
    user, redir = _console_guard(request, db)
    if redir:
        return redir
    email = cac_email.strip().lower()
    if not nom.strip() or not email:
        return RedirectResponse("/console?err=champs", status_code=302)
    if db.query(_User).filter_by(email=email).first():
        return RedirectResponse("/console?err=email", status_code=302)
    if len(cac_password) < 8:
        return RedirectResponse("/console?err=mdp", status_code=302)
    cab = Cabinet(nom=nom.strip(), pays=pays.strip() or "France",
                  devise_defaut=(devise_defaut.strip()[:3] or "EUR").upper(),
                  referentiel_defaut=referentiel_defaut.strip() or "PCG_FR")
    db.add(cab)
    db.flush()
    cac = _User(email=email, hashed_password=hash_password(cac_password),
                nom_complet=cac_nom.strip() or email, is_active=True,
                lang=user.lang, cabinet_id=cab.id)
    admin_role = db.query(_Role).filter_by(code="ADMIN").first()
    if admin_role:
        cac.roles.append(admin_role)
    db.add(cac)
    journaliser(db, user_id=user.id, action="cabinet.creer", objet="cabinet",
                detail=f"{cab.nom} / CAC {email}")
    db.commit()
    return RedirectResponse("/console", status_code=302)


@router.post("/console/cabinet/{cabinet_id}/toggle", include_in_schema=False)
async def console_cabinet_toggle(cabinet_id: int, request: Request, db: Session = Depends(get_db)):
    user, redir = _console_guard(request, db)
    if redir:
        return redir
    cab = db.get(Cabinet, cabinet_id)
    if cab:
        cab.is_archived = not cab.is_archived
        etat = "suspendu" if cab.is_archived else "actif"
        journaliser(db, user_id=user.id, action="cabinet.toggle", objet="cabinet",
                    detail=f"{cab.nom}:{etat}")
        db.commit()
    return RedirectResponse("/console", status_code=302)


@router.get("/missions/{mission_id}/vue/reclassement", include_in_schema=False)
def reclassement_page(mission_id: int, request: Request, db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    mission = _mission_ou_404(db, mission_id)
    lignes = (db.query(LigneBalance).filter_by(mission_id=mission_id)
              .order_by(LigneBalance.compte).all())
    rows = [{"id": lb.id, "compte": lb.compte, "libelle": lb.libelle,
             "solde_n": lb.solde_n, "cycle": cycle_pour_cs(lb.cs_standard)} for lb in lignes]
    cycles = [{"code": c, "libelle": libelle_cycle(c)} for c in CYCLES]
    # Récap : nombre de comptes par cycle (aide à repérer les classements douteux).
    compte_par_cycle: dict[str, int] = {}
    for r in rows:
        compte_par_cycle[r["cycle"]] = compte_par_cycle.get(r["cycle"], 0) + 1
    recap = [{"code": c, "libelle": libelle_cycle(c), "n": compte_par_cycle.get(c, 0)}
             for c in CYCLES if compte_par_cycle.get(c, 0)]
    return _templates.TemplateResponse(request, "reclassement.html", {
        "lang": user.lang, "user": user, "mission": mission, "rows": rows,
        "cycles": cycles, "recap": recap})


@router.post("/missions/{mission_id}/vue/reclassement/masse", include_in_schema=False)
async def reclassement_masse(mission_id: int, request: Request, prefixe: str = Form(...),
                            cycle: str = Form(...), db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    if not db.get(Mission, mission_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mission introuvable")
    prefixe = (prefixe or "").strip()
    n = 0
    if prefixe and cycle in CYCLES:
        cs = cs_representatif(cycle)
        lignes = (db.query(LigneBalance)
                  .filter(LigneBalance.mission_id == mission_id,
                          LigneBalance.compte.startswith(prefixe)).all())
        for lb in lignes:
            lb.cs_standard = cs
            n += 1
        if n:
            journaliser(db, user_id=user.id, action="balance.reclasser_masse", objet="mission",
                        detail=f"{prefixe}*->{cycle} ({n})")
            db.commit()
    return RedirectResponse(
        f"/missions/{mission_id}/vue/reclassement?masse={n}", status_code=302)


@router.post("/missions/{mission_id}/vue/reclassement/{ligne_id}", include_in_schema=False)
async def reclassement_save(mission_id: int, ligne_id: int, request: Request,
                            cycle: str = Form(...), db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    lb = db.get(LigneBalance, ligne_id)
    if not lb or lb.mission_id != mission_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ligne introuvable")
    if cycle in CYCLES:
        lb.cs_standard = cs_representatif(cycle)
        journaliser(db, user_id=user.id, action="balance.reclasser", objet="ligne",
                    detail=f"{lb.compte}->{cycle}")
        db.commit()
    return RedirectResponse(f"/missions/{mission_id}/vue/reclassement", status_code=302)


@router.get("/missions/{mission_id}/vue/editions", include_in_schema=False)
def editions_page(mission_id: int, request: Request, db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    mission = _mission_ou_404(db, mission_id)
    editions = editions_service.lister(db, mission_id)
    return _templates.TemplateResponse(request, "editions.html", {
        "lang": user.lang, "user": user, "mission": mission, "editions": editions})


@router.post("/missions/{mission_id}/vue/documents/{doc_id}/ocr", include_in_schema=False)
def documents_ocr(mission_id: int, doc_id: int, request: Request, db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    doc = db.get(Document, doc_id)
    if not doc or doc.mission_id != mission_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document introuvable")
    res = ocr_service.extraire(document_service.chemin_absolu(doc), doc.type_doc)
    doc.texte_extrait = res["texte"] if res["statut"] == "ok" else ""
    doc.ocr_statut = res["statut"]
    doc.ocr_methode = res["methode"]
    db.commit()
    journaliser(db, user_id=user.id, action="document.ocr", objet="document", detail=res["statut"])
    return RedirectResponse(f"/missions/{mission_id}/vue/documents", status_code=302)


@router.post("/missions/{mission_id}/vue/documents/upload", include_in_schema=False)
async def documents_upload(mission_id: int, request: Request,
                           fichier: UploadFile = File(...), db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    _mission_ou_404(db, mission_id)
    form = await request.form()
    cycle_code = str(form.get("cycle_code", "") or "").strip()
    try:
        document_service.enregistrer(db, mission_id, fichier, cycle_code, user.id)
    except document_service.UploadInvalide as exc:
        return RedirectResponse(
            f"/missions/{mission_id}/vue/documents?err={exc}", status_code=302)
    journaliser(db, user_id=user.id, action="document.upload", objet="mission", detail=str(mission_id))
    return RedirectResponse(f"/missions/{mission_id}/vue/documents", status_code=302)


@router.get("/missions/{mission_id}/vue/documents/{doc_id}/download", include_in_schema=False)
def documents_download(mission_id: int, doc_id: int, request: Request, db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    doc = db.get(Document, doc_id)
    if not doc or doc.mission_id != mission_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document introuvable")
    chemin = document_service.chemin_absolu(doc)
    if not chemin.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Fichier absent du stockage")
    return FileResponse(chemin, filename=doc.nom,
                        media_type=doc.content_type or "application/octet-stream")


@router.post("/missions/{mission_id}/vue/documents/{doc_id}/delete", include_in_schema=False)
def documents_delete(mission_id: int, doc_id: int, request: Request, db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    doc = db.get(Document, doc_id)
    if doc and doc.mission_id == mission_id:
        document_service.supprimer(db, doc)
        journaliser(db, user_id=user.id, action="document.delete", objet="mission", detail=str(mission_id))
    return RedirectResponse(f"/missions/{mission_id}/vue/documents", status_code=302)


# =================================================== Veille réglementaire (Module 26)
@router.get("/vue/veille", response_class=HTMLResponse, include_in_schema=False)
def veille_page(request: Request, db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    ref = request.query_params.get("ref") or "TOUS"
    items = veille_service.lister(db, ref)
    return _templates.TemplateResponse(request, "veille.html", {
        "lang": user.lang, "user": user, "items": items, "ref": ref,
        "non_lus": sum(1 for i in items if not i.lu)})


@router.post("/vue/veille/init", include_in_schema=False)
def veille_init(request: Request, db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    veille_service.amorcer(db)
    return RedirectResponse("/vue/veille", status_code=302)


@router.post("/vue/veille/add", include_in_schema=False)
async def veille_add(request: Request, db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    form = await request.form()
    titre = str(form.get("titre", "") or "").strip()
    if titre:
        veille_service.creer(
            db, titre=titre, source=str(form.get("source", "") or "").strip(),
            referentiel=str(form.get("referentiel", "TRANSVERSE")),
            reference=str(form.get("reference", "") or "").strip(),
            resume=str(form.get("resume", "") or "").strip(),
            url=str(form.get("url", "") or "").strip(),
            impact=str(form.get("impact", "moyen")),
        )
    return RedirectResponse("/vue/veille", status_code=302)


@router.post("/vue/veille/{veille_id}/lu", include_in_schema=False)
async def veille_lu(veille_id: int, request: Request, db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    form = await request.form()
    veille_service.marquer_lu(db, veille_id, str(form.get("lu", "1")) == "1")
    return RedirectResponse("/vue/veille", status_code=302)


# ================================================================ Portail client
def _portail_mission(db: Session, mission_id: int, user) -> Mission:
    """Renvoie la mission si elle appartient au client de l'utilisateur, sinon 403/404."""
    m = db.get(Mission, mission_id)
    if not m:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dossier introuvable")
    if not user.client_id or m.client_id != user.client_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Accès restreint à vos dossiers")
    return m


@router.get("/portail", response_class=HTMLResponse, include_in_schema=False)
def portail_accueil(request: Request, db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    client = db.get(Client, user.client_id) if user.client_id else None
    missions = (db.query(Mission).filter_by(client_id=user.client_id).all()
                if user.client_id else [])
    return _templates.TemplateResponse(request, "portail.html", {
        "lang": user.lang, "user": user, "client": client, "missions": missions})


@router.get("/portail/missions/{mission_id}", response_class=HTMLResponse, include_in_schema=False)
def portail_mission(mission_id: int, request: Request, db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    mission = _portail_mission(db, mission_id, user)
    cycles = db.query(Cycle).filter_by(mission_id=mission_id).order_by(Cycle.code).all()
    docs = document_service.lister(db, mission_id)
    return _templates.TemplateResponse(request, "portail_mission.html", {
        "lang": user.lang, "user": user, "mission": mission, "cycles": cycles, "docs": docs,
        "err": request.query_params.get("err")})


@router.post("/portail/missions/{mission_id}/documents/upload", include_in_schema=False)
async def portail_upload(mission_id: int, request: Request,
                         fichier: UploadFile = File(...), db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    _portail_mission(db, mission_id, user)  # cloisonnement
    try:
        document_service.enregistrer(db, mission_id, fichier, "PORTAIL", user.id)
    except document_service.UploadInvalide as exc:
        return RedirectResponse(f"/portail/missions/{mission_id}?err={exc}", status_code=302)
    journaliser(db, user_id=user.id, action="portail.document.upload", objet="mission", detail=str(mission_id))
    return RedirectResponse(f"/portail/missions/{mission_id}", status_code=302)


@router.get("/portail/missions/{mission_id}/documents/{doc_id}/download", include_in_schema=False)
def portail_download(mission_id: int, doc_id: int, request: Request, db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    _portail_mission(db, mission_id, user)  # cloisonnement
    doc = db.get(Document, doc_id)
    if not doc or doc.mission_id != mission_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document introuvable")
    chemin = document_service.chemin_absolu(doc)
    if not chemin.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Fichier absent du stockage")
    return FileResponse(chemin, filename=doc.nom,
                        media_type=doc.content_type or "application/octet-stream")


@router.post("/missions/{mission_id}/fec-import", include_in_schema=False)
async def fec_import_web(mission_id: int, request: Request, fichier: UploadFile = File(...),
                        confirmer: str = Form(""), db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    if not db.get(Mission, mission_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mission introuvable")
    # Garde-fou : ne pas écraser une balance existante sans confirmation explicite.
    existe = db.query(LigneBalance).filter_by(mission_id=mission_id).first() is not None
    if existe and not confirmer:
        return RedirectResponse(f"/missions/{mission_id}/vue?fec=confirm", status_code=302)
    brut = await fichier.read()
    try:
        contenu = brut.decode("utf-8")
    except UnicodeDecodeError:
        contenu = brut.decode("latin-1", errors="replace")
    try:
        res = fec_import_service.importer_fec(db, mission_id, contenu)
    except Exception:  # noqa: BLE001 — FEC illisible : on revient sans planter
        return RedirectResponse(f"/missions/{mission_id}/vue?fec=erreur", status_code=302)
    journaliser(db, user_id=user.id, action="fec.import", objet="mission",
                detail=f"{res['nb_comptes']} comptes")
    db.commit()
    eq = "1" if res["equilibre"] else "0"
    return RedirectResponse(
        f"/missions/{mission_id}/vue?fec=ok&comptes={res['nb_comptes']}"
        f"&ecritures={res['nb_ecritures']}&equilibre={eq}"
        f"&rn={res['resultat_net']:.0f}&ca={res['chiffre_affaires']:.0f}"
        f"&cp={res['capitaux_propres']:.0f}", status_code=302)


@router.post("/missions/{mission_id}/import-web", include_in_schema=False)
async def import_web(mission_id: int, request: Request, fichier: UploadFile = File(...),
                     feuille: str = Form("Table_BG"), db: Session = Depends(get_db)):
    user = _user_or_redirect(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    if not db.get(Mission, mission_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mission introuvable")
    contenu = await fichier.read()
    try:
        importer_balance(db, mission_id, contenu, feuille)
    except ValueError:
        pass  # l'utilisateur reverra la page ; message d'erreur possible en amélioration
    return RedirectResponse(f"/missions/{mission_id}/vue", status_code=302)
