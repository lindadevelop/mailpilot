"""API REST da Fase 1."""

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import SessionLocal
from ..models import Conversation, Message
from ..schemas import BatchIn, BatchOut, CompleteIn, SyncStatusOut
from ..services import import_service
from ..services import reports_service

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Autenticação por chave. Serviço privado nunca exposto sem autenticação."""
    expected = get_settings().api_key
    if not x_api_key or x_api_key != expected:
        raise HTTPException(status_code=401, detail='Chave de API inválida.')


@router.get('/health')
def health() -> dict:
    return {'status': 'ok', 'app': 'MailPilot AI'}


@router.post('/api/emails/batch', response_model=BatchOut, dependencies=[Depends(require_api_key)])
def import_emails(payload: BatchIn, db: Session = Depends(get_db)) -> BatchOut:
    """Recebe um lote de mensagens. Idempotente por (conta, origem, external_id)."""
    run, errors = import_service.import_batch(db, payload)
    return BatchOut(
        received=run.received,
        imported=run.imported,
        duplicated=run.duplicated,
        failed=run.failed,
        sync_run_id=run.id,
        errors=errors[:20],
    )


@router.get('/api/sync/status', response_model=SyncStatusOut, dependencies=[Depends(require_api_key)])
def sync_status(
    account_email: str | None = Query(default=None),
    source: str | None = Query(default='import'),
    db: Session = Depends(get_db),
) -> SyncStatusOut:
    return import_service.get_sync_status(db, account_email, source)


@router.post('/api/sync/complete', dependencies=[Depends(require_api_key)])
def sync_complete(payload: CompleteIn, db: Session = Depends(get_db)) -> dict:
    run = import_service.finish_sync(db, str(payload.account_email), payload.source, payload.sync_run_id, payload.notes)
    if run is None:
        raise HTTPException(status_code=404, detail='Execução de sincronização não encontrada.')
    return {'sync_run_id': run.id, 'status': run.status, 'imported': run.imported, 'failed': run.failed}


@router.get('/api/conversations', dependencies=[Depends(require_api_key)])
def list_conversations(
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    state: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> dict:
    stmt = select(Conversation).order_by(Conversation.last_message_at.desc().nullslast(), Conversation.id.desc())
    if state:
        stmt = stmt.where(Conversation.state == state)
    rows = db.scalars(stmt.limit(limit).offset(offset)).all()
    total = db.scalar(select(func.count(Conversation.id))) or 0
    # Quem escreveu: a contraparte (última mensagem recebida) e o autor da última
    # mensagem, para a lista dizer de quem é o email sem abrir a conversa.
    remetentes = reports_service.remetentes_por_conversa(db, [c.id for c in rows])
    return {
        'total': total,
        'items': [
            {
                'id': c.id,
                'subject': c.subject,
                'sender': remetentes.get(c.id, {}).get('sender'),
                'last_sender': remetentes.get(c.id, {}).get('last_sender'),
                'last_direction': remetentes.get(c.id, {}).get('last_direction'),
                'unread': remetentes.get(c.id, {}).get('unread', 0),
                'state': c.state,
                'message_count': c.message_count,
                'last_message_at': c.last_message_at.isoformat() if c.last_message_at else None,
            }
            for c in rows
        ],
    }


@router.get('/api/reports/subjects', dependencies=[Depends(require_api_key)])
def relatorio_assuntos(limite: int = Query(default=50, le=200), db: Session = Depends(get_db)) -> dict:
    """Resumo por assunto: quantos temas, quem escreve e o que exige ação."""
    return reports_service.resumo_por_assunto(db, limite)


@router.get('/api/dashboard', dependencies=[Depends(require_api_key)])
def dashboard(db: Session = Depends(get_db)) -> dict:
    """Página inicial orientada à ação: o que exige atenção agora."""
    total_messages = db.scalar(select(func.count(Message.id))) or 0
    unread = db.scalar(select(func.count(Message.id)).where(Message.is_read.is_(False))) or 0
    by_state: dict[str, int] = {}
    for state, count in db.execute(
        select(Conversation.state, func.count(Conversation.id)).group_by(Conversation.state)
    ).all():
        by_state[state or 'Indeterminado'] = count
    return {
        'total_messages': total_messages,
        'unread_messages': unread,
        'conversations_by_state': by_state,
        # A Fase 2 preenche estes indicadores com a classificação por IA
        'preciso_responder': by_state.get('Preciso responder', 0),
        'aguardo_terceiros': by_state.get('Aguardo resposta de terceiros', 0),
        'atrasados': 0,
    }
