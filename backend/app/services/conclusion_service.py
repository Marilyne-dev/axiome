"""Service des conclusions par cycle (upsert + lecture pour la note de synthèse)."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.cycles_ref import libelle_cycle
from app.models.conclusion import CycleConclusion


def enregistrer(db: Session, mission_id: int, cycle_code: str,
                conclusion: str, anomalie: bool) -> CycleConclusion:
    obj = db.query(CycleConclusion).filter_by(mission_id=mission_id, cycle_code=cycle_code).first()
    if not obj:
        obj = CycleConclusion(mission_id=mission_id, cycle_code=cycle_code)
        db.add(obj)
    obj.conclusion = conclusion
    obj.anomalie = anomalie
    db.commit(); db.refresh(obj)
    return obj


def lister(db: Session, mission_id: int) -> dict[str, CycleConclusion]:
    rows = db.query(CycleConclusion).filter_by(mission_id=mission_id).all()
    return {r.cycle_code: r for r in rows}


def pour_note_synthese(db: Session, mission_id: int) -> list[dict]:
    return [
        {"cycle": libelle_cycle(r.cycle_code), "conclusion": r.conclusion, "anomalie": r.anomalie}
        for r in db.query(CycleConclusion).filter_by(mission_id=mission_id).all()
        if r.conclusion
    ]
