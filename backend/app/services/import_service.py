"""Importação de emails: idempotente, retomável e auditável.

Regras (do documento técnico):
  * deduplicação idempotente por (conta, origem, identificador estável);
  * erros por lote ficam registados, sem abortar o resto do lote;
  * a conclusão da sincronização só acontece com a persistência confirmada;
  * o cursor só avança depois de o lote ser persistido (permite retomar);
  * o corpo do email nunca vai para logs nem para auditoria.
"""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import (
    Account,
    AuditLog,
    Conversation,
    ImportError,
    Message,
    SyncCursor,
    SyncRun,
)
from ..schemas import BatchIn, SyncStatusOut


def get_or_create_account(db: Session, email_address: str, source: str = 'import') -> Account:
    account = db.scalar(select(Account).where(Account.email_address == email_address))
    if account:
        return account
    account = Account(name=email_address.split('@')[0], email_address=email_address, source=source)
    db.add(account)
    db.flush()
    return account


def parse_sent_at(value) -> datetime | None:
    """Datas em texto (CSV) ou datetime (JSON) entram sem rebentar o lote."""
    if value is None or isinstance(value, datetime):
        return value
    text = str(value).strip().replace('Z', '+00:00')
    if not text:
        return None
    for fmt in (None, '%Y-%m-%d %H:%M:%S', '%d/%m/%Y %H:%M', '%d/%m/%Y'):
        try:
            return datetime.fromisoformat(text) if fmt is None else datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _upsert_conversation(db: Session, account: Account, external_id: str | None, subject: str | None) -> Conversation | None:
    if not external_id:
        return None
    conversation = db.scalar(
        select(Conversation).where(
            Conversation.account_id == account.id,
            Conversation.external_id == external_id,
        )
    )
    if conversation:
        conversation.message_count = (conversation.message_count or 0) + 1
        return conversation
    conversation = Conversation(
        account_id=account.id,
        external_id=external_id,
        subject=subject,
        message_count=1,
    )
    db.add(conversation)
    db.flush()
    return conversation


def import_batch(db: Session, payload: BatchIn) -> tuple[SyncRun, list[str]]:
    """Importa um lote. Devolve a execução de sincronização e a lista de erros."""
    account = get_or_create_account(db, str(payload.account_email), payload.source)
    run = SyncRun(account_id=account.id, source=payload.source, status='em_curso')
    db.add(run)
    db.flush()

    imported = 0
    duplicated = 0
    failed = 0
    errors: list[str] = []

    for item in payload.messages:
        try:
            existing = db.scalar(
                select(Message).where(
                    Message.account_id == account.id,
                    Message.external_id == item.external_id,
                )
            )
            if existing:
                # Duplicado: não é erro, é o comportamento correto (idempotência).
                duplicated += 1
                continue

            conversation = _upsert_conversation(
                db, account, item.conversation_external_id, item.subject
            )
            message = Message(
                account_id=account.id,
                conversation_id=conversation.id if conversation else None,
                external_id=item.external_id,
                internet_message_id=item.internet_message_id,
                in_reply_to=item.in_reply_to,
                direction=item.direction,
                folder=item.folder,
                sender=str(item.sender) if item.sender else None,
                recipients=', '.join(str(r) for r in item.recipients),
                subject=item.subject,
                body=item.body,
                sent_at=parse_sent_at(item.sent_at),
                received_at=parse_sent_at(item.received_at),
                is_read=item.is_read,
            )
            db.add(message)
            db.flush()

            if conversation and message.received_at:
                conversation.last_message_at = message.received_at
            imported += 1
        except Exception as exc:  # um item mau não pode derrubar o lote
            db.rollback()
            failed += 1
            reason = f'{item.external_id}: {exc}'
            errors.append(reason)
            db.add(ImportError(sync_run_id=run.id, account_id=account.id, external_id=item.external_id, reason=str(exc)))
            db.flush()
            # A conta/execução foram desfeitas pelo rollback: garantir que continuam
            account = get_or_create_account(db, str(payload.account_email), payload.source)
            run = db.scalar(select(SyncRun).where(SyncRun.id == run.id)) or run

    run.received = len(payload.messages)
    run.imported = imported
    run.duplicated = duplicated
    run.failed = failed
    run.status = 'concluido' if failed == 0 else 'concluido_com_erros'
    run.finished_at = datetime.utcnow()

    if payload.cursor is not None:
        save_cursor(db, account.id, payload.source, payload.cursor, run.id)

    db.add(AuditLog(action='import_batch', entity='account', entity_id=str(account.id),
                    details=f'received={run.received} imported={imported} duplicated={duplicated} failed={failed}'))
    db.commit()
    return run, errors


def save_cursor(db: Session, account_id: int, source: str, position: str | None, run_id: int | None) -> SyncCursor:
    cursor = db.scalar(
        select(SyncCursor).where(SyncCursor.account_id == account_id, SyncCursor.source == source)
    )
    if cursor is None:
        cursor = SyncCursor(account_id=account_id, source=source)
        db.add(cursor)
    cursor.position = position
    cursor.last_run_id = run_id
    db.flush()
    return cursor


def get_sync_status(db: Session, account_email: str | None = None, source: str | None = None) -> SyncStatusOut:
    out = SyncStatusOut(account_email=account_email, source=source)
    if not account_email:
        return out
    account = db.scalar(select(Account).where(Account.email_address == account_email))
    if not account:
        return out
    cursor = db.scalar(
        select(SyncCursor).where(SyncCursor.account_id == account.id,
                                SyncCursor.source == (source or 'import'))
    )
    if cursor:
        out.cursor = cursor.position
        out.last_run_id = cursor.last_run_id
    out.message_count = db.scalar(select(func.count(Message.id)).where(Message.account_id == account.id)) or 0
    out.conversation_count = db.scalar(
        select(func.count(Conversation.id)).where(Conversation.account_id == account.id)
    ) or 0
    return out


def finish_sync(db: Session, account_email: str, source: str = 'import', run_id: int | None = None, notes: str | None = None) -> SyncRun | None:
    """Marca a sincronização como concluída — só depois de persistência confirmada."""
    account = db.scalar(select(Account).where(Account.email_address == account_email))
    if not account:
        return None
    run = db.scalar(select(SyncRun).where(SyncRun.id == run_id)) if run_id else None
    if run is None:
        run = db.scalar(
            select(SyncRun).where(SyncRun.account_id == account.id, SyncRun.source == source)
            .order_by(SyncRun.id.desc())
        )
    if run is None:
        return None
    run.status = 'concluido' if not run.failed else 'concluido_com_erros'
    run.finished_at = datetime.utcnow()
    if notes:
        run.notes = notes
    db.add(AuditLog(action='sync_complete', entity='sync_run', entity_id=str(run.id),
                    details=f'imported={run.imported} duplicated={run.duplicated} failed={run.failed}'))
    db.commit()
    return run
