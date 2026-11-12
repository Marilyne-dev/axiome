"""Service CSRD : double matérialité et couverture des points ESRS.

Méthodologie de travail (non certifiante) : un thème est réputé matériel dès lors
que sa matérialité d'impact OU financière atteint le seuil (moyenne). Les points de
données ESRS ne sont générés que pour les thèmes retenus.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core import esrs_ref
from app.models.csrd import CsrdMateriality, CsrdPoint


def ensure_materialite(db: Session, mission_id: int) -> None:
    """Crée les lignes de matérialité pour tous les thèmes si absentes."""
    existants = {m.esrs_code for m in db.query(CsrdMateriality).filter_by(mission_id=mission_id).all()}
    ajout = False
    for code, _lib, _pil in esrs_ref.THEMES:
        if code not in existants:
            db.add(CsrdMateriality(mission_id=mission_id, esrs_code=code,
                                   impact=0, financier=0, retenu=False))
            ajout = True
    if ajout:
        db.commit()


def set_materialite(db: Session, mission_id: int, esrs_code: str,
                    impact: int, financier: int, justification: str = "") -> None:
    """Enregistre la double matérialité d'un thème puis synchronise les points."""
    impact = max(0, min(3, int(impact)))
    financier = max(0, min(3, int(financier)))
    row = (db.query(CsrdMateriality)
           .filter_by(mission_id=mission_id, esrs_code=esrs_code).first())
    if not row:
        row = CsrdMateriality(mission_id=mission_id, esrs_code=esrs_code)
        db.add(row)
    row.impact = impact
    row.financier = financier
    row.retenu = esrs_ref.est_materiel(impact, financier)
    row.justification = (justification or "").strip()[:500]
    db.commit()
    sync_points(db, mission_id)


def sync_points(db: Session, mission_id: int) -> None:
    """Aligne les points de données sur les thèmes retenus (ajout/suppression)."""
    retenus = {m.esrs_code for m in db.query(CsrdMateriality)
               .filter_by(mission_id=mission_id, retenu=True).all()}
    points = db.query(CsrdPoint).filter_by(mission_id=mission_id).all()
    presents = {(p.esrs_code, p.code) for p in points}
    # supprimer les points des thèmes non retenus
    for p in points:
        if p.esrs_code not in retenus:
            db.delete(p)
    # ajouter les points manquants des thèmes retenus
    for code in retenus:
        for pcode, plib in esrs_ref.points_du_theme(code):
            if (code, pcode) not in presents:
                db.add(CsrdPoint(mission_id=mission_id, esrs_code=code,
                                 code=pcode, libelle=plib, couvert=False))
    db.commit()


def toggle_point(db: Session, mission_id: int, point_id: int) -> None:
    p = db.get(CsrdPoint, point_id)
    if p and p.mission_id == mission_id:
        p.couvert = not p.couvert
        db.commit()


def etat(db: Session, mission_id: int) -> dict:
    """Synthèse : thèmes évalués, points par thème retenu, couverture, conclusion."""
    ensure_materialite(db, mission_id)
    mrows = {m.esrs_code: m for m in db.query(CsrdMateriality)
             .filter_by(mission_id=mission_id).all()}
    themes = []
    for code, lib, pil in esrs_ref.THEMES:
        m = mrows.get(code)
        themes.append({
            "code": code, "libelle": lib, "pilier": pil,
            "pilier_lib": esrs_ref.PILIERS.get(pil, pil),
            "impact": m.impact if m else 0,
            "financier": m.financier if m else 0,
            "retenu": m.retenu if m else False,
            "justification": m.justification if m else "",
        })
    retenus = [t for t in themes if t["retenu"]]
    points = db.query(CsrdPoint).filter_by(mission_id=mission_id).order_by(
        CsrdPoint.esrs_code, CsrdPoint.code).all()
    par_theme: dict[str, list] = {}
    for p in points:
        par_theme.setdefault(p.esrs_code, []).append(p)
    total = len(points)
    couverts = sum(1 for p in points if p.couvert)
    pct = round(100 * couverts / total) if total else 0
    if not retenus:
        conclusion = "Analyse de matérialité à réaliser."
    elif pct >= 100:
        conclusion = "Couverture complète des points de données des thèmes retenus."
    elif pct >= 50:
        conclusion = "Couverture partielle — poursuivre la collecte et les contrôles."
    else:
        conclusion = "Couverture insuffisante — diligences à approfondir."
    return {
        "themes": themes, "retenus": retenus, "nb_retenus": len(retenus),
        "points_par_theme": par_theme, "total_points": total,
        "couverts": couverts, "couverture_pct": pct, "conclusion": conclusion,
        "echelle": esrs_ref.ECHELLE,
    }
