"""Module 2 — Gestion des clients et de leurs entités rattachées."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.database import get_db
from app.models.client import Client
from app.models.client_details import CompteBancaire, Contact, Dirigeant
from app.models.user import User
from app.schemas.client import (
    ClientCreate,
    ClientOut,
    ClientUpdate,
    CompteBancaireIn,
    ContactIn,
    DirigeantIn,
)
from app.services.audit_service import journaliser

router = APIRouter(prefix="/clients", tags=["clients"])


def _get_client(db: Session, client_id: int) -> Client:
    client = db.get(Client, client_id)
    if not client:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Client introuvable")
    return client


@router.get("", response_model=list[ClientOut])
def list_clients(
    inclure_archives: bool = False,
    db: Session = Depends(get_db), _=Depends(require_permission("client:read")),
) -> list[Client]:
    q = db.query(Client)
    if not inclure_archives:
        q = q.filter(Client.is_archived.is_(False))
    return q.order_by(Client.raison_sociale).all()


@router.post("", response_model=ClientOut, status_code=status.HTTP_201_CREATED)
def create_client(
    data: ClientCreate, db: Session = Depends(get_db),
    user: User = Depends(require_permission("client:write")),
) -> Client:
    client = Client(cabinet_id=user.cabinet_id, **data.model_dump())
    db.add(client)
    db.flush()
    journaliser(db, user_id=user.id, action="client.create", objet="client", detail=client.raison_sociale)
    db.commit()
    db.refresh(client)
    return client


@router.patch("/{client_id}", response_model=ClientOut)
def update_client(
    client_id: int, data: ClientUpdate, db: Session = Depends(get_db),
    user: User = Depends(require_permission("client:write")),
) -> Client:
    client = _get_client(db, client_id)
    for champ, valeur in data.model_dump(exclude_unset=True).items():
        setattr(client, champ, valeur)
    journaliser(db, user_id=user.id, action="client.update", objet="client", detail=client.raison_sociale)
    db.commit()
    db.refresh(client)
    return client


@router.delete("/{client_id}")
def archive_client(
    client_id: int, db: Session = Depends(get_db),
    user: User = Depends(require_permission("client:write")),
) -> dict:
    """Archivage logique (jamais de suppression physique d'un dossier)."""
    client = _get_client(db, client_id)
    client.is_archived = True
    journaliser(db, user_id=user.id, action="client.archive", objet="client", detail=client.raison_sociale)
    db.commit()
    return {"id": client.id, "archived": True}


# --- Sous-ressources ---
@router.post("/{client_id}/contacts", status_code=status.HTTP_201_CREATED)
def add_contact(client_id: int, data: ContactIn, db: Session = Depends(get_db),
                _=Depends(require_permission("client:write"))) -> dict:
    _get_client(db, client_id)
    c = Contact(client_id=client_id, **data.model_dump())
    db.add(c); db.commit(); db.refresh(c)
    return {"id": c.id, "nom": c.nom, "fonction": c.fonction}


@router.post("/{client_id}/dirigeants", status_code=status.HTTP_201_CREATED)
def add_dirigeant(client_id: int, data: DirigeantIn, db: Session = Depends(get_db),
                  _=Depends(require_permission("client:write"))) -> dict:
    _get_client(db, client_id)
    d = Dirigeant(client_id=client_id, **data.model_dump())
    db.add(d); db.commit(); db.refresh(d)
    return {"id": d.id, "nom": d.nom, "mandat": d.mandat}


@router.post("/{client_id}/banques", status_code=status.HTTP_201_CREATED)
def add_banque(client_id: int, data: CompteBancaireIn, db: Session = Depends(get_db),
               _=Depends(require_permission("client:write"))) -> dict:
    _get_client(db, client_id)
    b = CompteBancaire(client_id=client_id, **data.model_dump())
    db.add(b); db.commit(); db.refresh(b)
    return {"id": b.id, "banque": b.banque, "iban": b.iban, "devise": b.devise}
