"""Journal des éditions — enregistrement et restitution des livrables générés."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.edition import RapportEdition


def enregistrer(db: Session, mission_id: int, type_edition: str, format: str, par: str) -> RapportEdition:
    """Consigne une édition de livrable (commit immédiat, journal immuable)."""
    edition = RapportEdition(
        mission_id=mission_id, type_edition=type_edition,
        format=(format or "").lower(), par=par or "—",
    )
    db.add(edition)
    db.commit()
    db.refresh(edition)
    return edition


def lister(db: Session, mission_id: int) -> list[RapportEdition]:
    """Éditions d'une mission, de la plus récente à la plus ancienne."""
    return (
        db.query(RapportEdition)
        .filter_by(mission_id=mission_id)
        .order_by(RapportEdition.created_at.desc(), RapportEdition.id.desc())
        .all()
    )


def exporter_csv(db: Session, mission_id: int) -> str:
    """Journal des éditions au format CSV (numérotation chronologique croissante)."""
    import csv
    import io

    editions = list(reversed(lister(db, mission_id)))  # plus ancienne = n°1
    buf = io.StringIO()
    writeur = csv.writer(buf, delimiter=";")
    writeur.writerow(["N°", "Date", "Heure", "Livrable", "Format", "Généré par"])
    for i, e in enumerate(editions, start=1):
        writeur.writerow([
            i,
            e.created_at.strftime("%d/%m/%Y"),
            e.created_at.strftime("%H:%M"),
            e.type_edition,
            e.format,
            e.par,
        ])
    return buf.getvalue()
