"""Fase 5: rascunhos (nunca enviados), modos e relatório de alterações."""

import json

from sqlalchemy import select

from app.ai.drafting import validate_draft
from app.models import Conversation
from app.models_drafting import ReplyDraft
from app.services import drafting_service, import_service


class ProviderFalso:
    def __init__(self, resposta):
        self.resposta = resposta
        self.prompts: list[str] = []

    def classificar(self, system_prompt, user_prompt):
        self.prompts.append(user_prompt)
        return self.resposta


def _resposta(
    corpo=(
        'Bom dia,\n\nSegue a proposta solicitada. Confirmo a entrega até sexta-feira.\n\n'
        'Com os melhores cumprimentos,'
    )
):
    return json.dumps(
        {
            'subject': 'Re: Proposta',
            'body': corpo,
            'facts_used': ['O cliente pediu proposta', 'Prazo: sexta-feira'],
            'open_questions': [],
        }
    )


def test_gera_rascunho_para_revisao(db, payload_factory):
    import_service.import_batch(db, payload_factory(['d1'], conversation_external_id='conv-d'))
    conversa = db.scalar(select(Conversation))
    provider = ProviderFalso(_resposta())

    resultado = drafting_service.gerar_rascunho(db, conversa.id, provider, modo='tecnico', model_name='teste')

    assert resultado['ok'] is True
    assert resultado['status'] == 'rascunho'
    assert 'não é enviado' in resultado['aviso'].lower() or 'Nada é enviado' in resultado['aviso']
    rascunho = db.scalar(select(ReplyDraft))
    assert rascunho.mode == 'tecnico'
    assert rascunho.status == 'rascunho'
    assert 'sexta-feira' in rascunho.body


def test_prompt_inclui_modo_e_conversa(db, payload_factory):
    import_service.import_batch(db, payload_factory(['d1'], conversation_external_id='conv-d'))
    conversa = db.scalar(select(Conversation))
    provider = ProviderFalso(_resposta())
    drafting_service.gerar_rascunho(db, conversa.id, provider, modo='diplomatico')
    assert 'MODO: diplomatico' in provider.prompts[0]
    assert 'CONVERSA' in provider.prompts[0]


def test_modo_invalido_e_recusado(db, payload_factory):
    import_service.import_batch(db, payload_factory(['d1'], conversation_external_id='conv-d'))
    conversa = db.scalar(select(Conversation))
    resultado = drafting_service.gerar_rascunho(db, conversa.id, ProviderFalso(_resposta()), modo='agressivo')
    assert resultado['ok'] is False
    assert db.scalar(select(ReplyDraft)) is None


def test_rascunho_invalido_nao_e_guardado(db, payload_factory):
    import_service.import_batch(db, payload_factory(['d1'], conversation_external_id='conv-d'))
    conversa = db.scalar(select(Conversation))
    resultado = drafting_service.gerar_rascunho(db, conversa.id, ProviderFalso('{"body": "curto"}'))
    assert resultado['ok'] is False
    assert db.scalar(select(ReplyDraft)) is None


def test_validacao_recusa_corpo_curto():
    import pytest

    with pytest.raises(ValueError):
        validate_draft({'body': 'ok'}, 'objetivo')


def test_revisao_e_descarte_sao_registados(db, payload_factory):
    import_service.import_batch(db, payload_factory(['d1'], conversation_external_id='conv-d'))
    conversa = db.scalar(select(Conversation))
    r = drafting_service.gerar_rascunho(db, conversa.id, ProviderFalso(_resposta()))
    revisto = drafting_service.marcar_revisto(db, r['draft_id'], 'carlos')
    assert revisto['status'] == 'revisto'
    descartado = drafting_service.marcar_revisto(db, r['draft_id'], 'carlos', descartar=True)
    assert descartado['status'] == 'descartado'


def test_nenhum_rascunho_e_enviado(db, payload_factory):
    """Não existe (nem deve existir) qualquer função de envio nesta fase."""
    import inspect

    nomes = [n for n, f in inspect.getmembers(drafting_service, inspect.isfunction)]
    assert not any('send' in n or 'enviar' in n for n in nomes)


def test_relatorio_de_alteracoes(db, payload_factory):
    import_service.import_batch(db, payload_factory(['d1'], conversation_external_id='conv-d'))
    conversa = db.scalar(select(Conversation))
    provider = ProviderFalso(
        json.dumps({'state': 'Preciso responder', 'confidence': 0.8,
                    'evidence': [{'message_id': 1, 'quote': 'Podem enviar proposta até sexta-feira'}]})
    )
    from app.services import analysis_service

    analysis_service.run_analysis(db, provider)

    relatorio = drafting_service.relatorio_alteracoes(db, horas=24)
    assert relatorio['janela_horas'] == 24
    assert relatorio['total_reanalises'] >= 1
    assert 'Preciso responder' in relatorio['por_estado']
