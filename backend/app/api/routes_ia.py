"""Modules 14/16 — Assistant IA : aide ponctuelle et conversations enregistrées."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.conversation_ia import ConversationIA, MessageIA
from app.models.user import User
from app.services.ia_service import assister, converser, ia_disponible

router = APIRouter(prefix="/ia", tags=["assistant_ia"])
_log = logging.getLogger("axiome.ia")
_MAX_MESSAGES = 200


class AssistIn(BaseModel):
    prompt: str
    contexte: str = ""


class MessageIn(BaseModel):
    contenu: str = Field(..., min_length=1, max_length=8000)
    contexte: str = Field("", max_length=8000)


@router.get("/statut")
def statut(_: User = Depends(get_current_user)) -> dict:
    return {"disponible": ia_disponible()}


@router.post("/assister")
def assister_ia(data: AssistIn, _: User = Depends(get_current_user)) -> dict:
    """Aide rédactionnelle IA ponctuelle (l'humain valide toujours)."""
    return assister(data.prompt, data.contexte)


# ---- Conversations enregistrées (propres à l'utilisateur connecté) ----

def _conversation(db: Session, user: User, cid: int) -> ConversationIA:
    """Conversation de l'utilisateur, sinon 404 (on ne révèle pas celles des autres)."""
    c = db.get(ConversationIA, cid)
    if not c or c.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation introuvable")
    return c


def _message(m: MessageIA) -> dict:
    return {"id": m.id, "role": m.role, "contenu": m.contenu,
            "created_at": m.created_at.isoformat() if m.created_at else None}


@router.get("/conversations")
def lister_conversations(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[dict]:
    rows = (db.query(ConversationIA).filter_by(user_id=user.id)
            .order_by(ConversationIA.updated_at.desc(), ConversationIA.id.desc()).limit(100).all())
    return [{"id": c.id, "titre": c.titre,
             "updated_at": c.updated_at.isoformat() if c.updated_at else None} for c in rows]


@router.post("/conversations", status_code=status.HTTP_201_CREATED)
def creer_conversation(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    c = ConversationIA(user_id=user.id, titre="")
    db.add(c)
    db.commit()
    db.refresh(c)
    return {"id": c.id, "titre": c.titre}


@router.get("/conversations/{cid}")
def lire_conversation(cid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    c = _conversation(db, user, cid)
    return {"id": c.id, "titre": c.titre, "messages": [_message(m) for m in c.messages]}


@router.post("/conversations/{cid}/messages")
def envoyer_message(cid: int, data: MessageIn, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)) -> dict:
    """Ajoute la question, interroge l'IA avec tout l'historique, enregistre la réponse."""
    c = _conversation(db, user, cid)
    if not ia_disponible():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,
                            "Assistant IA non configuré (ANTHROPIC_API_KEY absente).")
    if len(c.messages) >= _MAX_MESSAGES:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "Conversation trop longue : commencez-en une nouvelle.")
    question = data.contenu.strip()
    if not question:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Message vide.")
    historique = [{"role": m.role, "contenu": m.contenu} for m in c.messages]
    historique.append({"role": "user", "contenu": question})
    res = converser(historique, data.contexte)
    if res.get("erreur") or not (res.get("reponse") or "").strip():
        _log.warning("assistant IA : échec (%s)", res.get("erreur", "réponse vide"))
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "L'assistant n'a pas pu répondre. Réessayez dans un instant.")
    u = MessageIA(conversation_id=c.id, role="user", contenu=question)
    a = MessageIA(conversation_id=c.id, role="assistant", contenu=res["reponse"])
    db.add_all([u, a])
    if not c.titre:
        c.titre = question.replace("\n", " ")[:60]
    c.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(u)
    db.refresh(a)
    return {"conversation": {"id": c.id, "titre": c.titre}, "messages": [_message(u), _message(a)],
            "avertissement": res.get("avertissement", "")}


@router.delete("/conversations/{cid}")
def supprimer_conversation(cid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    c = _conversation(db, user, cid)
    db.delete(c)
    db.commit()
    return {"ok": True}
