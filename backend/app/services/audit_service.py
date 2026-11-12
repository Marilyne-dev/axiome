"""Service de journalisation : centralise l'écriture du journal d'audit."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.audit import AuditLog


def journaliser(db: Session, *, user_id: int | None, action: str,
                objet: str = "", detail: str = "", ip: str = "") -> None:
    """Ajoute une entrée au journal d'audit (sans committer : appelant maître de la transaction)."""
    db.add(AuditLog(user_id=user_id, action=action, objet=objet, detail=detail, ip=ip))
