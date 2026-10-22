"""Endpoints da Fase 2."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..ai.ollama import OllamaClient, OllamaError
from ..models_analysis import AiAnalysis, AiAnalysisEvidence
from ..services import analysis_service
from .routes import get_db, require_api_key

router = APIRouter(dependencies=[Depends(require_api_key)])


class AnalysisRunIn(BaseModel):
    limit: int = 20
    account_email: str | None = None


@router.post('/api/analysis/run')
def run_analysis(payload: AnalysisRunIn, db: Session = Depends(get_db)) -> dict:
    """Corre o classificador nas conversas com mensagens novas."""
    cliente = OllamaClient()
    if not cliente.disponivel():
        raise HTTPException(
            status_code=503,
            detail='O Ollama não está acessível. Arranque-o (ollama serve) e confirme OLLAMA_BASE_URL.',
        )
    try:
        resultado = analysis_service.run_analysis(db, cliente, limite=payload.limit, model_name=cliente.model)
    except OllamaError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return resultado


@router.get('/api/conversations/{conversation_id}/analysis')
def conversation_analysis(conversation_id: int, db: Session = Depends(get_db)) -> dict:
    analise = db.scalar(
        select(AiAnalysis).where(AiAnalysis.conversation_id == conversation_id).order_by(AiAnalysis.id.desc())
    )
    if not analise:
        return {'conversation_id': conversation_id, 'analysis': None}
    evidencias = db.scalars(
        select(AiAnalysisEvidence).where(AiAnalysisEvidence.analysis_id == analise.id)
    ).all()
    return {
        'conversation_id': conversation_id,
        'analysis': {
            'id': analise.id,
            'state': analise.state,
            'reason': analise.reason,
            'confidence': analise.confidence,
            'deadline_text': analise.deadline_text,
            'commitments': analise.commitments,
            'model': analise.model,
            'created_at': analise.created_at.isoformat() if analise.created_at else None,
            'evidence': [{'message_id': e.message_id, 'quote': e.quote} for e in evidencias],
        },
    }


@router.get('/api/pending')
def pending(
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
) -> dict:
    """Pendências que exigem ação (o dashboard da Fase 1 passa a ter dados reais)."""
    from ..models import Conversation

    exigem_acao = ['Preciso responder', 'Preciso executar tarefa', 'Aguardo resposta de terceiros', 'Acompanhar']
    conversas = db.scalars(
        select(Conversation)
        .where(Conversation.state.in_(exigem_acao))
        .order_by(Conversation.last_message_at.desc().nullslast())
        .limit(limit)
    ).all()
    return {
        'total': len(conversas),
        'items': [
            {'id': c.id, 'subject': c.subject, 'state': c.state, 'message_count': c.message_count}
            for c in conversas
        ],
    }
