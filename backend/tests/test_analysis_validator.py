"""Validação da resposta da IA: nada de JSON inventado, estados falsos ou prazos inventados."""

import pytest

from app.ai.validator import AnalysisError, extract_json, validate_analysis

IDS = {10, 11, 12}


def test_extrai_json_simples():
    assert extract_json('{"state": "Resolvido"}')['state'] == 'Resolvido'


def test_extrai_json_com_cerca_de_codigo():
    bruto = '```json\n{"state": "Informativo", "confidence": 0.9}\n```'
    assert extract_json(bruto)['state'] == 'Informativo'


def test_extrai_json_com_texto_a_volta():
    bruto = 'Claro, aqui está:\n{"state": "Acompanhar", "confidence": 0.5}\nEspero ter ajudado.'
    assert extract_json(bruto)['state'] == 'Acompanhar'


def test_resposta_vazia_e_recusada():
    with pytest.raises(AnalysisError):
        extract_json('   ')


def test_json_invalido_e_recusado():
    with pytest.raises(AnalysisError):
        extract_json('{isto não é json}')


def test_estado_inexistente_e_recusado():
    with pytest.raises(AnalysisError):
        validate_analysis({'state': 'Talvez responda', 'confidence': 0.5}, IDS)


def test_confianca_fora_do_intervalo_e_recusada():
    with pytest.raises(AnalysisError):
        validate_analysis({'state': 'Resolvido', 'confidence': 1.7}, IDS)


def test_evidencia_de_outra_conversa_e_recusada():
    dados = {
        'state': 'Preciso responder',
        'confidence': 0.8,
        'evidence': [{'message_id': 999, 'quote': 'excerto'}],
    }
    with pytest.raises(AnalysisError):
        validate_analysis(dados, IDS)


def test_prazo_sem_evidencia_e_ignorado():
    """Não se inventam prazos: sem citação que os sustente, ficam nulos."""
    resultado = validate_analysis(
        {'state': 'Preciso responder', 'confidence': 0.7, 'deadline_text': 'sexta-feira'}, IDS
    )
    assert resultado['deadline_text'] is None


def test_prazo_com_evidencia_e_aceite():
    resultado = validate_analysis(
        {
            'state': 'Preciso responder',
            'confidence': 0.9,
            'deadline_text': 'até sexta-feira',
            'evidence': [{'message_id': 11, 'quote': 'podem enviar até sexta-feira?'}],
        },
        IDS,
    )
    assert resultado['deadline_text'] == 'até sexta-feira'
    assert resultado['evidence'][0]['message_id'] == 11


def test_estado_indeterminado_e_aceite():
    resultado = validate_analysis({'state': 'Indeterminado', 'confidence': 0.2}, IDS)
    assert resultado['state'] == 'Indeterminado'


def test_listas_sao_normalizadas():
    resultado = validate_analysis(
        {
            'state': 'Preciso responder',
            'confidence': 0.8,
            'questions': ['Qual o prazo?', ''],
            'partial_answers': 'não é lista',
        },
        IDS,
    )
    assert resultado['questions'] == ['Qual o prazo?']
    assert resultado['partial_answers'] == []
