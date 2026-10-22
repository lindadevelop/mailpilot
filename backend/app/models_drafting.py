"""Fase 5 — rascunhos de resposta. NUNCA são enviados automaticamente."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base

DRAFT_MODES = ('objetivo', 'diplomatico', 'tecnico', 'firme_cordial')


class ReplyDraft(Base):
    __tablename__ = 'reply_drafts'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey('conversations.id'), nullable=False)
    mode: Mapped[str] = mapped_column(String(20), nullable=False)
    subject: Mapped[str | None] = mapped_column(String(300))
    body: Mapped[str] = mapped_column(Text, nullable=False)
    # O que a IA usou como factos vs. o que é sugestão de redação
    facts_used: Mapped[str | None] = mapped_column(Text)
    model: Mapped[str | None] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(20), default='rascunho', nullable=False)  # rascunho | revisto | descartado
    reviewed_by: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (Index('ix_reply_drafts_conversation', 'conversation_id', 'created_at'),)
