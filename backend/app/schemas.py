"""Payloads da API (validação estrita)."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class EmailIn(BaseModel):
    """Uma mensagem recebida da origem. `external_id` tem de ser estável."""

    external_id: str = Field(min_length=1, max_length=400)
    internet_message_id: str | None = None
    in_reply_to: str | None = None
    conversation_external_id: str | None = None
    direction: str = Field(default='in', pattern='^(in|out)$')
    folder: str | None = None
    sender: EmailStr | None = None
    recipients: list[EmailStr] = Field(default_factory=list)
    subject: str | None = None
    body: str | None = None
    sent_at: datetime | None = None
    received_at: datetime | None = None
    is_read: bool = False


class BatchIn(BaseModel):
    account_email: EmailStr
    source: str = Field(default='import', max_length=50)
    messages: list[EmailIn] = Field(default_factory=list, max_length=500)
    # Posição a guardar no cursor no fim do lote (opaca para o MailPilot)
    cursor: str | None = None


class BatchOut(BaseModel):
    received: int
    imported: int
    duplicated: int
    failed: int
    sync_run_id: int
    errors: list[str] = Field(default_factory=list)


class SyncStatusOut(BaseModel):
    account_email: str | None = None
    source: str | None = None
    cursor: str | None = None
    last_run_id: int | None = None
    message_count: int = 0
    conversation_count: int = 0


class CompleteIn(BaseModel):
    account_email: EmailStr
    source: str = 'import'
    sync_run_id: int | None = None
    notes: str | None = None
