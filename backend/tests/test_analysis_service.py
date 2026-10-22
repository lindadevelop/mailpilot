"""Serviço de análise: incremental, correções manuais e resposta inválida."""

import json

from sqlalchemy import func, select

from app.models import Message
from app.models_analysis import AiAnalysis, AiAnalysisEvidence, ManualCorrection
from app.services import analysis_service, import_service
from app.services.analysis_service import run_analysis


class ProviderFalso:
    """Devolve o que lhe mandarem; conta quantas vezes foi chamado."""

    def __init__(self, resposta: str):
        self.resposta = resposta
        self.chamadas = 0
        self.prompts: list[str] = []

    def classificar(self, system_prompt: str, user_prompt: str) -> str:
        self.chamadas += 1
        self.prompts.append(user_prompt)
        return self.resposta


def _resposta_para(message_id: int, state: str = 'Preciso responder') -> str:
    return json.dumps(
        {
            'state': state,
            'reason': 'O cliente pediu proposta e não houve resposta.',
            'confidence': 0.86,
            'questions': ['Prazo para proposta'],
            'partial_answers': [],
            'commitments': [],
            'deadline_text': None,
            'evidence': [{'message_id': message_id, 'quote': 'Podem enviar proposta até sexta-feira'}],
        }
    )


def test_analisa_e_guarda_estado_evidencias(db, payload_factory):
    import_service.import_batch(db, payload_factory(['m1'], conversation_external_id='conv-1'))
    mensagem = db.scalar(select(Message))
    provider = ProviderFalso(_resposta_para(mensagem.id))

    resultado = run_analysis(db, provider, model_name='teste')

    assert resultado['analisadas'] == 1
    assert db.scalar(select(AiAnalysis)).state == 'Preciso responder'
    assert db.scalar(select(func.count(AiAnalysisEvidence.id))) == 1
    # O estado da conversa passa a ser o classificado
    from app.models import Conversation

    assert db.scalar(select(Conversation)).state == 'Preciso responder'


def test_prompt_inclui_a_conversa_completa_e_ids(db, payload_factory):
    import_service.import_batch(db, payload_factory(['m1', 'm2'], conversation_external_id='conv-1'))
    provider = ProviderFalso(_resposta_para(1))
    run_analysis(db, provider)
    prompt = provider.prompts[0]
    assert 'CONVERSA' in prompt
    assert 'message_id=' in prompt
    assert 'Podem enviar proposta até sexta-feira?' in prompt


def test_analise_e_incremental_nao_repete(db, payload_factory):
    import_service.import_batch(db, payload_factory(['m1'], conversation_external_id='conv-1'))
    provider = ProviderFalso(_resposta_para(1))

    run_analysis(db, provider)
    assert provider.chamadas == 1

    # Sem mensagens novas, não volta a analisar
    segunda = run_analysis(db, provider)
    assert provider.chamadas == 1
    assert segunda['analisadas'] == 0

    # Com mensagem nova, volta a analisar
    import_service.import_batch(db, payload_factory(['m2'], conversation_external_id='conv-1'))
    nova = db.scalars(select(Message).order_by(Message.id)).all()[-1]
    provider.resposta = _resposta_para(nova.id, state='Resolvido')
    terceira = run_analysis(db, provider)
    assert provider.chamadas == 2
    assert terceira['analisadas'] == 1
    assert db.scalar(select(AiAnalysis).order_by(AiAnalysis.id.desc())).state == 'Resolvido'


def test_correcao_manual_nao_e_substituida_pela_ia(db, payload_factory):
    from app.models import Conversation

    import_service.import_batch(db, payload_factory(['m1'], conversation_external_id='conv-1'))
    conversa = db.scalar(select(Conversation))
    conversa.state = 'Acompanhar'
    db.add(ManualCorrection(conversation_id=conversa.id, state='Acompanhar', note='conferido por mim'))
    db.commit()

    provider = ProviderFalso(_resposta_para(1, state='Resolvido'))
    resultado = run_analysis(db, provider)

    assert resultado['analisadas'] == 0
    assert resultado['resultados'][0]['motivo'] == 'correcao_manual_ativa'
    assert provider.chamadas == 0
    assert conversa.state == 'Acompanhar'


def test_resposta_invalida_nao_e_guardada(db, payload_factory):
    import_service.import_batch(db, payload_factory(['m1'], conversation_external_id='conv-1'))
    provider = ProviderFalso('Desculpe, não consigo classificar isto agora.')

    resultado = run_analysis(db, provider)

    assert resultado['analisadas'] == 0
    assert 'resposta_invalida' in resultado['resultados'][0]['motivo']
    assert db.scalar(select(func.count(AiAnalysis.id))) == 0


def test_estado_nao_muda_quando_a_ia_falha(db, payload_factory):
    from app.models import Conversation

    import_service.import_batch(db, payload_factory(['m1'], conversation_external_id='conv-1'))
    provider = ProviderFalso('{"state": "EstadoQueNaoExiste", "confidence": 0.5}')
    run_analysis(db, provider)
    assert db.scalar(select(Conversation)).state == 'Indeterminado'
