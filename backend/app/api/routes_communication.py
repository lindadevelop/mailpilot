"""Endpoints da Fase 4 (contactos e comunicação)."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..ai.ollama import OllamaClient, OllamaError
from ..models_communication import CommunicationEvidence, CommunicationProfile
from ..services import communication_service
from .routes import get_db, require_api_key

router = APIRouter(dependencies=[Depends(require_api_key)])


class ConfirmIn(BaseModel):
    disc_hypothesis: str
    reviewed_by: str
    notes: str | None = None


class DisableIn(BaseModel):
    reviewed_by: str


@router.post('/api/contacts/{contact_id}/communication/analyze')
def analisar(contact_id: int, db: Session = Depends(get_db)) -> dict:
    cliente = OllamaClient()
    if not cliente.disponivel():
        raise HTTPException(status_code=503, detail='Ollama indisponível.')
    try:
        return communication_service.analisar_contacto(db, contact_id, cliente, cliente.model)
    except OllamaError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get('/api/contacts/{contact_id}/communication')
def ver(contact_id: int, db: Session = Depends(get_db)) -> dict:
    perfil = db.scalar(select(CommunicationProfile).where(CommunicationProfile.contact_id == contact_id))
    if perfil is None:
        return {'contact_id': contact_id, 'profile': None}
    evidencias = db.scalars(select(CommunicationEvidence).where(CommunicationEvidence.profile_id == perfil.id)).all()
    return {
        'contact_id': contact_id,
        'profile': {
            'formality': perfil.formality,
            'concise': perfil.concise,
            'prefers_detail': perfil.prefers_detail,
            'mentions_deadlines': perfil.mentions_deadlines,
            'explicit_requests': perfil.explicit_requests,
            'disc_hypothesis': perfil.disc_hypothesis,
            'disc_confidence': perfil.disc_confidence,
            'disc_reason': perfil.disc_reason,
            'status': perfil.status,
            'is_enabled': perfil.is_enabled,
            'model': perfil.model,
            'disclaimer': perfil.notes,
            'evidence': [{'message_id': e.message_id, 'quote': e.quote, 'aspect': e.aspect} for e in evidencias],
        },
    }


@router.post('/api/contacts/{contact_id}/communication/confirm')
def confirmar(contact_id: int, payload: ConfirmIn, db: Session = Depends(get_db)) -> dict:
    resultado = communication_service.confirmar_perfil(db, contact_id, payload.disc_hypothesis, payload.reviewed_by, payload.notes)
    if not resultado.get('ok'):
        raise HTTPException(status_code=400, detail=resultado.get('error'))
    return resultado


@router.post('/api/contacts/{contact_id}/communication/disable')
def desativar(contact_id: int, payload: DisableIn, db: Session = Depends(get_db)) -> dict:
    resultado = communication_service.desativar_perfil(db, contact_id, payload.reviewed_by)
    if not resultado.get('ok'):
        raise HTTPException(status_code=400, detail=resultado.get('error'))
    return resultado
