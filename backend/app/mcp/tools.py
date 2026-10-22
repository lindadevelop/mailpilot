"""As quatro ferramentas MCP, implementadas sobre a CAMADA DE SERVIÇOS.

Regra do documento técnico: o servidor MCP **não escreve diretamente na base de
dados** — invoca os mesmos serviços que a API REST (importação idempotente,
cursores e conclusão de sincronização). Assim há um só caminho para os dados.

Este módulo é puro Python (sem SDK), para poder ser testado sem transporte MCP.
"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import ImportError, SyncRun
from ..schemas import BatchIn, EmailIn
from ..services import import_service


def import_emails(
    db: Session,
    account_email: str,
    messages: list[dict[str, Any]],
    source: str = 'grok',
    cursor: str | None = None,
) -> dict[str, Any]:
    """Recebe um lote de mensagens vindas do Grok. Idempotente por documento."""
    if not account_email or '@' not in account_email:
        return {'ok': False, 'error': 'account_email inválido.'}
    if not isinstance(messages, list) or not messages:
        return {'ok': False, 'error': 'messages tem de ser uma lista não vazia.'}

    try:
        payload = BatchIn(
            account_email=account_email,
            source=source,
            cursor=cursor,
            messages=[EmailIn(**m) for m in messages],
        )
    except Exception as exc:  # payload inválido do cliente: devolver erro, não rebentar
        return {'ok': False, 'error': f'payload inválido: {exc}'}

    run, errors = import_service.import_batch(db, payload)
    return {
        'ok': True,
        'sync_run_id': run.id,
        'received': run.received,
        'imported': run.imported,
        'duplicated': run.duplicated,
        'failed': run.failed,
        'cursor': cursor,
        'errors': errors[:20],
    }


def get_sync_cursor(db: Session, account_email: str, source: str = 'grok') -> dict[str, Any]:
    """Devolve o cursor para o cliente retomar a importação onde parou."""
    estado = import_service.get_sync_status(db, account_email, source)
    return {
        'ok': True,
        'account_email': account_email,
        'source': source,
        'cursor': estado.cursor,
        'last_run_id': estado.last_run_id,
        'message_count': estado.message_count,
        'conversation_count': estado.conversation_count,
    }


def finish_sync(
    db: Session,
    account_email: str,
    source: str = 'grok',
    sync_run_id: int | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    """Marca a sincronização como concluída — só depois de persistência confirmada."""
    run = import_service.finish_sync(db, account_email, source, sync_run_id, notes)
    if run is None:
        return {'ok': False, 'error': 'Execução de sincronização não encontrada.'}
    return {
        'ok': True,
        'sync_run_id': run.id,
        'status': run.status,
        'imported': run.imported,
        'duplicated': run.duplicated,
        'failed': run.failed,
    }


def get_import_errors(db: Session, limit: int = 20, sync_run_id: int | None = None) -> dict[str, Any]:
    """Erros de importação, para o cliente poder corrigir e reenviar."""
    limite = max(1, min(int(limit or 20), 200))
    stmt = select(ImportError).order_by(ImportError.id.desc()).limit(limite)
    if sync_run_id is not None:
        stmt = stmt.where(ImportError.sync_run_id == sync_run_id)
    erros = db.scalars(stmt).all()
    return {
        'ok': True,
        'total': len(erros),
        'errors': [
            {
                'id': e.id,
                'sync_run_id': e.sync_run_id,
                'external_id': e.external_id,
                'reason': e.reason,
                'created_at': e.created_at.isoformat() if e.created_at else None,
            }
            for e in erros
        ],
    }


def ultima_execucao(db: Session, account_email: str, source: str = 'grok') -> dict[str, Any] | None:
    """Auxiliar de diagnóstico (não é ferramenta MCP)."""
    run = db.scalar(
        select(SyncRun).where(SyncRun.source == source).order_by(SyncRun.id.desc())
    )
    if run is None:
        return None
    return {
        'sync_run_id': run.id,
        'status': run.status,
        'received': run.received,
        'imported': run.imported,
        'duplicated': run.duplicated,
        'failed': run.failed,
    }
