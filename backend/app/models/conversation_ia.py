"""Assistant IA : conversations et messages enregistrés, propres à chaque utilisateur."""
from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class ConversationIA(Base, TimestampMixin):
    __tablename__ = "ia_conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    titre: Mapped[str] = mapped_column(String(200), default="")
    messages: Mapped[list["MessageIA"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", order_by="MessageIA.id")


class MessageIA(Base, TimestampMixin):
    __tablename__ = "ia_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("ia_conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(10), nullable=False)   # user | assistant
    contenu: Mapped[str] = mapped_column(Text, default="")
    conversation: Mapped[ConversationIA] = relationship(back_populates="messages")
