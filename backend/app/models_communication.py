"""Fase 4 — preferências de comunicação e hipóteses DISC.

Enquadramento (documento técnico, secção 7): isto é uma **hipótese de estilo de
comunicação observável**, nunca um diagnóstico, um traço psicológico definitivo nem
instrumento de avaliação de colaboradores. Cada hipótese tem confiança e citações,
pode ser revista, desativada ou corrigida por contacto, e não é usada para decisões
laborais.
"""

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

# Hipóteses permitidas (D, I, S, C, combinação ou indeterminado)
DISC_HYPOTHESES = ('D', 'I', 'S', 'C', 'combinacao', 'Indeterminado')


class CommunicationProfile(Base):
    """Perfil de comunicação de um contacto. Um por contacto."""

    __tablename__ = 'communication_profiles'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    contact_id: Mapped[int] = mapped_column(ForeignKey('contacts.id'), nullable=False)
    # Preferências observáveis (não são traços de personalidade)
    formality: Mapped[str | None] = mapped_column(String(20))  # formal | informal | Indeterminado
    concise: Mapped[bool | None] = mapped_column(Boolean)
    prefers_detail: Mapped[bool | None] = mapped_column(Boolean)
    mentions_deadlines: Mapped[bool | None] = mapped_column(Boolean)
    explicit_requests: Mapped[bool | None] = mapped_column(Boolean)
    notes: Mapped[str | None] = mapped_column(Text)
    # DISC como hipótese
    disc_hypothesis: Mapped[str | None] = mapped_column(String(20))
    disc_confidence: Mapped[float | None] = mapped_column(Float)
    disc_reason: Mapped[str | None] = mapped_column(Text)
    # Estado editorial: é uma sugestão até alguém confirmar
    status: Mapped[str] = mapped_column(String(20), default='sugestao', nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    model: Mapped[str | None] = mapped_column(String(80))
    reviewed_by: Mapped[str | None] = mapped_column(String(120))
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (UniqueConstraint('contact_id', name='uq_communication_profile_contact'),)


class CommunicationEvidence(Base):
    """Citação que sustenta uma preferência/hipótese."""

    __tablename__ = 'communication_evidence'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey('communication_profiles.id'), nullable=False)
    message_id: Mapped[int] = mapped_column(ForeignKey('messages.id'), nullable=False)
    quote: Mapped[str | None] = mapped_column(Text)
    aspect: Mapped[str | None] = mapped_column(String(40))  # formalidade, concisao, prazos, disc

    __table_args__ = (Index('ix_comm_evidence_profile', 'profile_id'),)
