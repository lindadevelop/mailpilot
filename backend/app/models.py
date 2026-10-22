"""Modelo de dados da Fase 1."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class Account(Base):
    """Conta de email importada (a origem dos dados)."""

    __tablename__ = 'accounts'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email_address: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    source: Mapped[str] = mapped_column(String(50), default='import', nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Company(Base):
    __tablename__ = 'companies'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    domain: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Contact(Base):
    __tablename__ = 'contacts'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email_address: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    display_name: Mapped[str | None] = mapped_column(String(200))
    company_id: Mapped[int | None] = mapped_column(ForeignKey('companies.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Conversation(Base):
    __tablename__ = 'conversations'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey('accounts.id'), nullable=False)
    external_id: Mapped[str] = mapped_column(String(400), nullable=False)
    subject: Mapped[str | None] = mapped_column(String(500))
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime)
    message_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Estado de pendência (Fase 2 preenche; na Fase 1 fica Indeterminado)
    state: Mapped[str] = mapped_column(String(40), default='Indeterminado', nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (UniqueConstraint('account_id', 'external_id', name='uq_conversation_external'),)


class Message(Base):
    __tablename__ = 'messages'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey('accounts.id'), nullable=False)
    conversation_id: Mapped[int | None] = mapped_column(ForeignKey('conversations.id'))
    # Identificador estável na origem: é a base da deduplicação idempotente
    external_id: Mapped[str] = mapped_column(String(400), nullable=False)
    internet_message_id: Mapped[str | None] = mapped_column(String(400))
    in_reply_to: Mapped[str | None] = mapped_column(String(400))
    direction: Mapped[str] = mapped_column(String(10), default='in', nullable=False)
    folder: Mapped[str | None] = mapped_column(String(120))
    sender: Mapped[str | None] = mapped_column(String(320))
    recipients: Mapped[str | None] = mapped_column(Text)
    subject: Mapped[str | None] = mapped_column(String(500))
    body: Mapped[str | None] = mapped_column(Text)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime)
    received_at: Mapped[datetime | None] = mapped_column(DateTime)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Estado de pendência por mensagem (Fase 2); Indeterminado na Fase 1
    pendency_state: Mapped[str] = mapped_column(String(40), default='Indeterminado', nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        # AQUI está a garantia de não duplicar: a mesma mensagem (conta + origem +
        # identificador estável) nunca entra duas vezes, mesmo que o lote seja reenviado.
        UniqueConstraint('account_id', 'external_id', name='uq_message_external'),
        Index('ix_messages_conversation', 'conversation_id'),
        Index('ix_messages_sent_at', 'sent_at'),
    )


class ConversationParticipant(Base):
    __tablename__ = 'conversation_participants'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey('conversations.id'), nullable=False)
    email_address: Mapped[str] = mapped_column(String(320), nullable=False)
    role: Mapped[str | None] = mapped_column(String(40))

    __table_args__ = (UniqueConstraint('conversation_id', 'email_address', name='uq_participant'),)


class SyncRun(Base):
    __tablename__ = 'sync_runs'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey('accounts.id'), nullable=False)
    source: Mapped[str] = mapped_column(String(50), default='import', nullable=False)
    status: Mapped[str] = mapped_column(String(30), default='em_curso', nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    received: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    imported: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duplicated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)


class SyncCursor(Base):
    """Permite retomar uma importação sem repetir o que já entrou."""

    __tablename__ = 'sync_cursors'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey('accounts.id'), nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    position: Mapped[str | None] = mapped_column(String(400))
    last_run_id: Mapped[int | None] = mapped_column(ForeignKey('sync_runs.id'))
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (UniqueConstraint('account_id', 'source', name='uq_cursor_account_source'),)


class ImportError(Base):
    __tablename__ = 'import_errors'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sync_run_id: Mapped[int | None] = mapped_column(ForeignKey('sync_runs.id'))
    account_id: Mapped[int | None] = mapped_column(ForeignKey('accounts.id'))
    external_id: Mapped[str | None] = mapped_column(String(400))
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class AuditLog(Base):
    """Auditoria — nunca guarda corpo de email."""

    __tablename__ = 'audit_log'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    entity: Mapped[str | None] = mapped_column(String(80))
    entity_id: Mapped[str | None] = mapped_column(String(80))
    details: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
