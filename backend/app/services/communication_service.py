"""Fase 4 — analisar a comunicação de um contacto e guardar a hipótese."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..ai.communication import PROMPT_VERSION_COM, SYSTEM_PROMPT_COM, build_contact_prompt, validate_communication
from ..ai.validator import AnalysisError, extract_json
from ..models import AuditLog, Contact, Message
from ..models_communication import CommunicationEvidence, CommunicationProfile

DISCLAIMER = (
    'Hipótese de estilo de comunicação observável, gerada a partir de mensagens '
    'profissionais. Não é diagnóstico, não é traço psicológico definitivo e não deve '
    'ser usada para decisões laborais ou de desempenho.'
)


def mensagens_do_contacto(db: Session, contact_id: int, limite: int = 60) -> tuple[list[dict], dict[int, str]]:
    contacto = db.get(Contact, contact_id)
    if contacto is None:
        return [], {}
    endereco = contacto.email_address
    linhas = db.scalars(
        select(Message)
        .where(Message.sender == endereco)
        .order_by(Message.received_at.asc().nullslast(), Message.id.asc())
        .limit(limite)
    ).all()
    mensagens = [
        {
            'id': m.id,
            'subject': m.subject,
            'body': m.body,
            'received_at': m.received_at.isoformat() if m.received_at else None,
            'sent_at': m.sent_at.isoformat() if m.sent_at else None,
        }
        for m in linhas
    ]
    return mensagens, {m['id']: (m['body'] or '') for m in mensagens}


def analisar_contacto(db: Session, contact_id: int, provider, model_name: str = 'desconhecido') -> dict:
    contacto = db.get(Contact, contact_id)
    if contacto is None:
        return {'contact_id': contact_id, 'aplicado': False, 'motivo': 'contacto_inexistente'}

    perfil = db.scalar(select(CommunicationProfile).where(CommunicationProfile.contact_id == contact_id))
    if perfil and perfil.status == 'confirmado':
        # Uma revisão humana confirmada não é substituída pela IA.
        return {'contact_id': contact_id, 'aplicado': False, 'motivo': 'perfil_confirmado'}

    mensagens, corpos = mensagens_do_contacto(db, contact_id)
    if not mensagens:
        return {'contact_id': contact_id, 'aplicado': False, 'motivo': 'sem_mensagens_do_contacto'}

    try:
        bruto = provider.classificar(SYSTEM_PROMPT_COM, build_contact_prompt(mensagens))
        dados = validate_communication(extract_json(bruto), corpos)
    except (AnalysisError, ValueError) as exc:
        db.add(AuditLog(action='communication_invalid', entity='contact', entity_id=str(contact_id), details=str(exc)))
        db.commit()
        return {'contact_id': contact_id, 'aplicado': False, 'motivo': f'resposta_invalida: {exc}'}

    if perfil is None:
        perfil = CommunicationProfile(contact_id=contact_id)
        db.add(perfil)
        db.flush()

    perfil.formality = dados['formality']
    perfil.concise = dados['concise']
    perfil.prefers_detail = dados['prefers_detail']
    perfil.mentions_deadlines = dados['mentions_deadlines']
    perfil.explicit_requests = dados['explicit_requests']
    perfil.disc_hypothesis = dados['disc_hypothesis']
    perfil.disc_confidence = dados['disc_confidence']
    perfil.disc_reason = dados['reason']
    perfil.status = 'sugestao'
    perfil.model = model_name
    perfil.notes = DISCLAIMER

    db.query(CommunicationEvidence).filter_by(profile_id=perfil.id).delete()
    for ev in dados['evidence']:
        db.add(CommunicationEvidence(profile_id=perfil.id, message_id=ev['message_id'],
                                     quote=ev['quote'], aspect=ev['aspect']))

    db.add(AuditLog(action='communication_analyzed', entity='contact', entity_id=str(contact_id),
                    details=f"disc={dados['disc_hypothesis']} confianca={dados['disc_confidence']}"))
    db.commit()
    return {'contact_id': contact_id, 'aplicado': True, 'disc_hypothesis': dados['disc_hypothesis'],
            'disc_confidence': dados['disc_confidence'], 'motivo': None}


def confirmar_perfil(db: Session, contact_id: int, disc_hypothesis: str, reviewed_by: str, notes: str | None = None) -> dict:
    """Correção/revisão humana: passa a valer e a IA deixa de o substituir."""
    from ..models_communication import DISC_HYPOTHESES

    if disc_hypothesis not in DISC_HYPOTHESES:
        return {'ok': False, 'error': f'Hipótese inválida: {disc_hypothesis}'}
    perfil = db.scalar(select(CommunicationProfile).where(CommunicationProfile.contact_id == contact_id))
    if perfil is None:
        return {'ok': False, 'error': 'Este contacto ainda não tem perfil.'}
    perfil.disc_hypothesis = disc_hypothesis
    perfil.status = 'confirmado'
    perfil.reviewed_by = reviewed_by
    if notes:
        perfil.notes = notes
    db.add(AuditLog(action='communication_confirmed', entity='contact', entity_id=str(contact_id),
                    details=f'disc={disc_hypothesis} revisto_por={reviewed_by}'))
    db.commit()
    return {'ok': True, 'contact_id': contact_id, 'disc_hypothesis': disc_hypothesis, 'status': 'confirmado'}


def desativar_perfil(db: Session, contact_id: int, reviewed_by: str) -> dict:
    perfil = db.scalar(select(CommunicationProfile).where(CommunicationProfile.contact_id == contact_id))
    if perfil is None:
        return {'ok': False, 'error': 'Sem perfil para este contacto.'}
    perfil.is_enabled = False
    perfil.reviewed_by = reviewed_by
    db.add(AuditLog(action='communication_disabled', entity='contact', entity_id=str(contact_id),
                    details=f'desativado por {reviewed_by}'))
    db.commit()
    return {'ok': True, 'contact_id': contact_id, 'is_enabled': False}
