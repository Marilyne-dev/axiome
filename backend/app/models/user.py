"""RBAC : utilisateurs, rôles, permissions et tables d'association."""
from __future__ import annotations

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin

# Associations n-n
user_roles = Table(
    "user_roles", Base.metadata,
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)

role_permissions = Table(
    "role_permissions", Base.metadata,
    Column("role_id", ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
)


class Permission(Base):
    """Permission atomique de la forme 'domaine:action' (ex. 'mission:read')."""

    __tablename__ = "permissions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    description: Mapped[str] = mapped_column(String(255), default="")


class Role(Base):
    """Rôle métier regroupant des permissions."""

    __tablename__ = "roles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    libelle: Mapped[str] = mapped_column(String(120), nullable=False)

    permissions: Mapped[list[Permission]] = relationship(secondary=role_permissions, lazy="selectin")


class User(Base, TimestampMixin, SoftDeleteMixin):
    """Utilisateur du cabinet (créé et géré par l'ADMINISTRATEUR)."""

    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)  # bcrypt, jamais en clair
    nom_complet: Mapped[str] = mapped_column(String(150), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # MFA
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    mfa_secret: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Langue préférée (i18n)
    lang: Mapped[str] = mapped_column(String(5), default="fr")

    cabinet_id: Mapped[int | None] = mapped_column(ForeignKey("cabinets.id", ondelete="SET NULL"), nullable=True)
    bureau_id: Mapped[int | None] = mapped_column(ForeignKey("bureaux.id", ondelete="SET NULL"), nullable=True)
    client_id: Mapped[int | None] = mapped_column(Integer, nullable=True)  # portail : client rattaché (sans FK, souplesse SQLite)

    roles: Mapped[list[Role]] = relationship(secondary=user_roles, lazy="selectin")

    def has_role(self, code: str) -> bool:
        return any(r.code == code for r in self.roles)

    def permission_codes(self) -> set[str]:
        return {p.code for r in self.roles for p in r.permissions}

    def has_permission(self, code: str) -> bool:
        return code in self.permission_codes()
