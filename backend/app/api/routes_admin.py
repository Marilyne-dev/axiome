"""Module 1 — Administration du cabinet (réservé à l'ADMIN / permission user:manage)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.database import get_db
from app.core.security import hash_password
from app.models.cabinet import Cabinet
from app.models.user import Role, User
from app.schemas.admin import CabinetUpdate, UserCreate, UserOut, UserUpdate
from app.services.audit_service import journaliser

router = APIRouter(prefix="/admin", tags=["administration"])


def _to_out(u: User) -> UserOut:
    return UserOut(
        id=u.id, email=u.email, nom_complet=u.nom_complet,
        is_active=u.is_active, roles=[r.code for r in u.roles], lang=u.lang,
    )


def _resolve_roles(db: Session, codes: list[str]) -> list[Role]:
    roles = db.query(Role).filter(Role.code.in_(codes)).all()
    trouves = {r.code for r in roles}
    manquants = set(codes) - trouves
    if manquants:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"Rôles inconnus : {sorted(manquants)}")
    return roles


@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), _=Depends(require_permission("user:manage"))) -> list[UserOut]:
    return [_to_out(u) for u in db.query(User).order_by(User.id).all()]


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    data: UserCreate, request: Request, db: Session = Depends(get_db),
    admin: User = Depends(require_permission("user:manage")),
) -> UserOut:
    """Création d'un compte par l'administrateur (mot de passe haché en bcrypt)."""
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "E-mail déjà utilisé")
    user = User(
        email=data.email, hashed_password=hash_password(data.password),
        nom_complet=data.nom_complet, lang=data.lang, is_active=True,
        cabinet_id=admin.cabinet_id,
    )
    user.roles = _resolve_roles(db, data.roles)
    db.add(user)
    db.flush()
    journaliser(db, user_id=admin.id, action="user.create", objet="user", detail=user.email,
                ip=request.client.host if request.client else "")
    db.commit()
    db.refresh(user)
    return _to_out(user)


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: int, data: UserUpdate, db: Session = Depends(get_db),
    admin: User = Depends(require_permission("user:manage")),
) -> UserOut:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Utilisateur introuvable")
    if data.nom_complet is not None:
        user.nom_complet = data.nom_complet
    if data.is_active is not None:
        user.is_active = data.is_active
    if data.lang is not None:
        user.lang = data.lang
    if data.roles is not None:
        user.roles = _resolve_roles(db, data.roles)
    journaliser(db, user_id=admin.id, action="user.update", objet="user", detail=user.email)
    db.commit()
    db.refresh(user)
    return _to_out(user)


@router.get("/roles")
def list_roles(db: Session = Depends(get_db), _=Depends(require_permission("user:manage"))) -> list[dict]:
    return [
        {"code": r.code, "libelle": r.libelle, "permissions": [p.code for p in r.permissions]}
        for r in db.query(Role).order_by(Role.code).all()
    ]


@router.patch("/cabinet/{cabinet_id}")
def update_cabinet(
    cabinet_id: int, data: CabinetUpdate, db: Session = Depends(get_db),
    admin: User = Depends(require_permission("cabinet:manage")),
) -> dict:
    cab = db.get(Cabinet, cabinet_id)
    if not cab:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cabinet introuvable")
    for champ, valeur in data.model_dump(exclude_unset=True).items():
        setattr(cab, champ, valeur)
    journaliser(db, user_id=admin.id, action="cabinet.update", objet="cabinet", detail=cab.nom)
    db.commit()
    return {"id": cab.id, "nom": cab.nom, "pays": cab.pays,
            "devise_defaut": cab.devise_defaut, "referentiel_defaut": cab.referentiel_defaut}
