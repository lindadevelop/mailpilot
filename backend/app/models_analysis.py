"""Fase 2 — análise por IA, evidências e correções manuais."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base

# Estados do classificador (documento técnico, secção 5)
PENDENCY_STATES = (
    'Preciso responder',
    'Aguardo resposta de terceiros',
    'Preciso executar tarefa',
    'Acompanhar',
    'Em análise',
    'Resolvido',
    'Informativo',
    'Indeterminado',
)


class AiAnalysis(Base):
    """Resultado de uma análise. Nunca substitui uma correção manual."""

    __tablename__ = 'ai_analyses'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey('conversations.id'), nullable=False)
    account_id: Mapped[int] = mapped_column(ForeignKey('accounts.id'), nullable=False)
    state: Mapped[str] = mapped_column(String(40), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float | None] = mapped_column(Float)
    # Prazo/compromisso só quando explicitamente presente na conversa
    deadline: Mapped[datetime | None] = mapped_column(DateTime)
    deadline_text: Mapped[str | None] = mapped_column(String(200))
    commitments: Mapped[str | None] = mapped_column(Text)
    model: Mapped[str | None] = mapped_column(String(80))
    prompt_version: Mapped[str | None] = mapped_column(String(20))
    # Última mensagem incluída: permite processamento incremental
    analysed_until_message_id: Mapped[int | None] = mapped_column(Integer)
    raw_response: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (Index('ix_ai_analyses_conversation', 'conversation_id', 'created_at'),)


class AiAnalysisEvidence(Base):
    """Citação que sustenta a classificação (mensagem + excerto)."""

    __tablename__ = 'ai_analysis_evidence'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    analysis_id: Mapped[int] = mapped_column(ForeignKey('ai_analyses.id'), nullable=False)
    message_id: Mapped[int] = mapped_column(ForeignKey('messages.id'), nullable=False)
    quote: Mapped[str | None] = mapped_column(Text)


class ManualCorrection(Base):
    """Correção feita por uma pessoa. Tem precedência sobre a IA."""

    __tablename__ = 'manual_corrections'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey('conversations.id'), nullable=False)
    state: Mapped[str] = mapped_column(String(40), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str | None] = mapped_column(String(120))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (UniqueConstraint('conversation_id', name='uq_manual_correction_conversation'),)
