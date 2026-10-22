"""Endpoints da Fase 5."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..ai.ollama import OllamaClient, OllamaError
from ..models_drafting import DRAFT_MODES, ReplyDraft
from ..services import drafting_service
from .routes import get_db, require_api_key

router = APIRouter(dependencies=[Depends(require_api_key)])


class DraftIn(BaseModel):
    mode: str = 'objetivo'
    instructions: str | None = None


class ReviewIn(BaseModel):
    reviewed_by: str
    discard: bool = False


@router.post('/api/conversations/{conversation_id}/draft')
def gerar(conversation_id: int, payload: DraftIn, db: Session = Depends(get_db)) -> dict:
    cliente = OllamaClient()
    if not cliente.disponivel():
        raise HTTPException(status_code=503, detail='Ollama indisponível.')
    if payload.mode not in DRAFT_MODES:
        raise HTTPException(status_code=400, detail=f'Modo inválido. Use: {", ".join(DRAFT_MODES)}')
    try:
        resultado = drafting_service.gerar_rascunho(
            db, conversation_id, cliente, payload.mode, payload.instructions, cliente.model
        )
    except OllamaError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    if not resultado.get('ok'):
        raise HTTPException(status_code=400, detail=resultado.get('error'))
    return resultado


@router.get('/api/conversations/{conversation_id}/drafts')
def listar(conversation_id: int, db: Session = Depends(get_db)) -> dict:
    rascunhos = db.scalars(
        select(ReplyDraft).where(ReplyDraft.conversation_id == conversation_id).order_by(ReplyDraft.id.desc())
    ).all()
    return {
        'total': len(rascunhos),
        'items': [
            {'id': r.id, 'mode': r.mode, 'subject': r.subject, 'body': r.body,
             'status': r.status, 'created_at': r.created_at.isoformat() if r.created_at else None}
            for r in rascunhos
        ],
    }


@router.post('/api/drafts/{draft_id}/review')
def rever(draft_id: int, payload: ReviewIn, db: Session = Depends(get_db)) -> dict:
    resultado = drafting_service.marcar_revisto(db, draft_id, payload.reviewed_by, payload.discard)
    if not resultado.get('ok'):
        raise HTTPException(status_code=404, detail=resultado.get('error'))
    return resultado


@router.get('/api/reports/changes')
def alteracoes(horas: int = Query(default=24, ge=1, le=720), db: Session = Depends(get_db)) -> dict:
    return drafting_service.relatorio_alteracoes(db, horas)
