"""Fase 4: hipótese DISC com citações, revisão humana e limites de uso."""

import json

import pytest
from sqlalchemy import select

from app.ai.communication import validate_communication
from app.models import Contact, Message
from app.models_communication import CommunicationEvidence, CommunicationProfile
from app.services import communication_service

CORPOS = {1: 'Exmos. Senhores, solicito a proposta com detalhe técnico completo. Cumprimentos.'}


def _resposta(quote='solicito a proposta com detalhe técnico completo', hipotese='C', confianca=0.7):
    return json.dumps(
        {
            'formality': 'formal',
            'concise': False,
            'prefers_detail': True,
            'mentions_deadlines': False,
            'explicit_requests': True,
            'disc_hypothesis': hipotese,
            'disc_confidence': confianca,
            'reason': 'Linguagem formal e pedido explícito de detalhe.',
            'evidence': [{'message_id': 1, 'quote': quote, 'aspect': 'formalidade'}],
        }
    )


class ProviderFalso:
    def __init__(self, resposta):
        self.resposta = resposta
        self.chamadas = 0

    def classificar(self, system_prompt, user_prompt):
        self.chamadas += 1
        return self.resposta


def test_valida_hipotese_com_citacao_literal():
    dados = validate_communication(json.loads(_resposta()), CORPOS)
    assert dados['disc_hypothesis'] == 'C'
    assert dados['disc_confidence'] == 0.7
    assert dados['evidence'][0]['aspect'] == 'formalidade'


def test_recusa_hipotese_invalida():
    with pytest.raises(ValueError):
        validate_communication(json.loads(_resposta(hipotese='INTJ')), CORPOS)


def test_recusa_citacao_inventada():
    with pytest.raises(ValueError):
        validate_communication(json.loads(_resposta(quote='pessoa muito analítica e reservada')), CORPOS)


def test_recusa_sem_evidencia():
    dados = json.loads(_resposta())
    dados['evidence'] = []
    with pytest.raises(ValueError):
        validate_communication(dados, CORPOS)


def test_recusa_evidencia_de_outra_mensagem():
    dados = json.loads(_resposta())
    dados['evidence'][0]['message_id'] = 999
    with pytest.raises(ValueError):
        validate_communication(dados, CORPOS)


def test_analisa_e_guarda_perfil_com_aviso_de_uso(db):
    contacto = Contact(email_address='ana@empresa.pt', display_name='Ana')
    db.add(contacto)
    db.flush()
    db.add(Message(account_id=1, external_id='c1', sender='ana@empresa.pt', subject='Pedido',
                   body=CORPOS[1], received_at=None, direction='in'))
    db.commit()
    mensagem = db.scalar(select(Message))

    contacto_id = contacto.id
    provider = ProviderFalso(_resposta())
    # a mensagem criada tem de ser a citada
    provider.resposta = _resposta().replace('"message_id": 1', f'"message_id": {mensagem.id}')
    resultado = communication_service.analisar_contacto(db, contacto_id, provider, 'teste')

    assert resultado['aplicado'] is True
    perfil = db.scalar(select(CommunicationProfile))
    assert perfil.disc_hypothesis == 'C'
    assert perfil.status == 'sugestao'
    assert 'não é diagnóstico' in (perfil.notes or '').lower()
    assert db.scalar(select(CommunicationEvidence)) is not None


def test_perfil_confirmado_nao_e_substituido_pela_ia(db):
    contacto = Contact(email_address='rui@empresa.pt', display_name='Rui')
    db.add(contacto)
    db.flush()
    db.add(Message(account_id=1, external_id='c2', sender='rui@empresa.pt', subject='Pedido',
                   body=CORPOS[1], direction='in'))
    db.commit()
    provider = ProviderFalso(_resposta())
    communication_service.analisar_contacto(db, contacto.id, provider)
    communication_service.confirmar_perfil(db, contacto.id, 'D', 'carlos')

    antes = provider.chamadas
    resultado = communication_service.analisar_contacto(db, contacto.id, provider)
    assert resultado['aplicado'] is False
    assert resultado['motivo'] == 'perfil_confirmado'
    assert provider.chamadas == antes
    assert db.scalar(select(CommunicationProfile)).disc_hypothesis == 'D'


def test_resposta_invalida_nao_cria_perfil(db):
    contacto = Contact(email_address='x@empresa.pt', display_name='X')
    db.add(contacto)
    db.flush()
    db.add(Message(account_id=1, external_id='c3', sender='x@empresa.pt', body=CORPOS[1], direction='in'))
    db.commit()

    resultado = communication_service.analisar_contacto(db, contacto.id, ProviderFalso('não sei'))
    assert resultado['aplicado'] is False
    assert 'resposta_invalida' in resultado['motivo']
    assert db.scalar(select(CommunicationProfile)) is None


def test_desativar_perfil(db):
    contacto = Contact(email_address='y@empresa.pt', display_name='Y')
    db.add(contacto)
    db.flush()
    db.add(Message(account_id=1, external_id='c4', sender='y@empresa.pt', body=CORPOS[1], direction='in'))
    db.commit()
    communication_service.analisar_contacto(db, contacto.id, ProviderFalso(_resposta()))
    assert communication_service.desativar_perfil(db, contacto.id, 'carlos')['ok'] is True
    assert db.scalar(select(CommunicationProfile)).is_enabled is False
