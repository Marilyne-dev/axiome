"""Objets transverses du dossier d'audit + journal d'audit inaltérable."""
from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class WorkingPaper(Base, TimestampMixin):
    """Feuille de travail (papier de travail) rattachée à un cycle."""

    __tablename__ = "working_papers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cycle_id: Mapped[int] = mapped_column(ForeignKey("cycles.id", ondelete="CASCADE"), nullable=False)
    reference: Mapped[str] = mapped_column(String(40), default="")   # ex. FMA, FMP
    titre: Mapped[str] = mapped_column(String(200), default="")
    contenu: Mapped[str] = mapped_column(Text, default="")
    statut: Mapped[str] = mapped_column(String(30), default="brouillon")


class Document(Base, TimestampMixin):
    """Document/GED rattaché à une mission."""

    __tablename__ = "documents"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mission_id: Mapped[int] = mapped_column(ForeignKey("missions.id", ondelete="CASCADE"), nullable=False)
    nom: Mapped[str] = mapped_column(String(255), nullable=False)
    chemin: Mapped[str] = mapped_column(String(500), default="")
    type_doc: Mapped[str] = mapped_column(String(60), default="")
    taille: Mapped[int] = mapped_column(Integer, default=0)               # octets
    content_type: Mapped[str] = mapped_column(String(120), default="")
    cycle_code: Mapped[str] = mapped_column(String(30), default="")       # rattachement cycle (optionnel)
    uploaded_by: Mapped[int | None] = mapped_column(Integer, nullable=True)  # id utilisateur (sans FK, souplesse SQLite)
    texte_extrait: Mapped[str] = mapped_column(Text, default="")           # OCR / extraction (recherche plein texte)
    ocr_statut: Mapped[str] = mapped_column(String(20), default="non_traite")  # non_traite|ok|vide|indisponible|erreur|non_supporte
    ocr_methode: Mapped[str] = mapped_column(String(20), default="")


class RiskItem(Base, TimestampMixin):
    """Élément de cartographie des risques."""

    __tablename__ = "risk_items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mission_id: Mapped[int] = mapped_column(ForeignKey("missions.id", ondelete="CASCADE"), nullable=False)
    libelle: Mapped[str] = mapped_column(String(255), nullable=False)
    categorie: Mapped[str] = mapped_column(String(60), default="")   # inherent, controle, fraude…
    probabilite: Mapped[int] = mapped_column(Integer, default=1)     # 1..5
    impact: Mapped[int] = mapped_column(Integer, default=1)          # 1..5

    @property
    def score(self) -> int:
        return self.probabilite * self.impact


class Sample(Base, TimestampMixin):
    """Échantillon (statistique/MUS/dirigé)."""

    __tablename__ = "samples"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cycle_id: Mapped[int] = mapped_column(ForeignKey("cycles.id", ondelete="CASCADE"), nullable=False)
    methode: Mapped[str] = mapped_column(String(40), default="aleatoire")
    taille: Mapped[int] = mapped_column(Integer, default=0)


class Confirmation(Base, TimestampMixin):
    """Circularisation / confirmation externe."""

    __tablename__ = "confirmations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mission_id: Mapped[int] = mapped_column(ForeignKey("missions.id", ondelete="CASCADE"), nullable=False)
    tiers: Mapped[str] = mapped_column(String(180), default="")
    type_tiers: Mapped[str] = mapped_column(String(40), default="banque")
    statut: Mapped[str] = mapped_column(String(30), default="envoyee")


class Recommendation(Base, TimestampMixin):
    """Recommandation / plan d'action (module 24)."""

    __tablename__ = "recommendations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mission_id: Mapped[int] = mapped_column(ForeignKey("missions.id", ondelete="CASCADE"), nullable=False)
    constat: Mapped[str] = mapped_column(Text, default="")
    recommandation: Mapped[str] = mapped_column(Text, default="")
    statut: Mapped[str] = mapped_column(String(30), default="ouverte")


class Threshold(Base, TimestampMixin):
    """Seuils (signification / planification / remontée) — module 27, paramétrables."""

    __tablename__ = "thresholds"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mission_id: Mapped[int] = mapped_column(ForeignKey("missions.id", ondelete="CASCADE"), nullable=False)
    seuil_signification: Mapped[float] = mapped_column(Float, default=0.0)
    seuil_planification: Mapped[float] = mapped_column(Float, default=0.0)
    seuil_remontee: Mapped[float] = mapped_column(Float, default=0.0)
    base_retenue: Mapped[str] = mapped_column(String(60), default="")   # ex. resultat_net


class AuditLog(Base, TimestampMixin):
    """Journal d'audit inaltérable : qui a fait quoi, quand (traçabilité RGPD/ISQM)."""

    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    objet: Mapped[str] = mapped_column(String(120), default="")
    detail: Mapped[str] = mapped_column(Text, default="")
    ip: Mapped[str] = mapped_column(String(45), default="")
