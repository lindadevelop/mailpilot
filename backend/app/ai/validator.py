"""Validação estrita das respostas da IA.

A IA é uma fonte não fiável: pode devolver texto à volta do JSON, estados
inexistentes, prazos inventados ou evidências que não existem na conversa. Nada
disso pode entrar na base de dados sem ser travado aqui.
"""

import json
import re
from typing import Any

from ..models_analysis import PENDENCY_STATES


class AnalysisError(ValueError):
    """Resposta da IA inválida — nunca se guarda análise inválida."""


def extract_json(texto: str) -> dict[str, Any]:
    """Extrai o primeiro objeto JSON da resposta (tolera cercas de código)."""
    if not texto or not texto.strip():
        raise AnalysisError('Resposta vazia da IA.')

    limpo = texto.strip()
    if limpo.startswith('```'):
        limpo = re.sub(r'^```[a-zA-Z]*\s*', '', limpo)
        limpo = re.sub(r'```\s*$', '', limpo).strip()

    try:
        dados = json.loads(limpo)
    except json.JSONDecodeError:
        inicio = limpo.find('{')
        fim = limpo.rfind('}')
        if inicio < 0 or fim <= inicio:
            raise AnalysisError('A resposta da IA não contém JSON.')
        try:
            dados = json.loads(limpo[inicio : fim + 1])
        except json.JSONDecodeError as exc:
            raise AnalysisError(f'JSON inválido na resposta da IA: {exc}') from exc

    if not isinstance(dados, dict):
        raise AnalysisError('A resposta da IA não é um objeto JSON.')
    return dados


def validate_analysis(dados: dict[str, Any], ids_validos: set[int]) -> dict[str, Any]:
    """Valida e normaliza o resultado. Lança `AnalysisError` se algo não bater certo."""
    estado = str(dados.get('state', '')).strip()
    if estado not in PENDENCY_STATES:
        raise AnalysisError(f'Estado inválido: {estado!r}')

    confianca = dados.get('confidence', 0.0)
    try:
        confianca = float(confianca)
    except (TypeError, ValueError):
        raise AnalysisError('Confiança não numérica.')
    if not 0.0 <= confianca <= 1.0:
        raise AnalysisError('Confiança fora do intervalo 0..1.')
    confianca = round(confianca, 2)

    evidencias: list[dict[str, Any]] = []
    for item in dados.get('evidence') or []:
        if not isinstance(item, dict):
            continue
        try:
            mid = int(item.get('message_id'))
        except (TypeError, ValueError):
            continue
        if mid not in ids_validos:
            # Evidência que não pertence à conversa: sinal de invenção — recusa tudo.
            raise AnalysisError(f'Evidência inválida: message_id {mid} não pertence à conversa.')
        quote = (item.get('quote') or '').strip()
        evidencias.append({'message_id': mid, 'quote': quote[:1000]})

    prazo_texto = dados.get('deadline_text')
    if prazo_texto is not None:
        prazo_texto = str(prazo_texto).strip() or None
    # Sem citações não há como sustentar um prazo: na dúvida, não se inventa.
    if prazo_texto and not evidencias:
        prazo_texto = None

    def _lista(valor: Any) -> list[str]:
        if not isinstance(valor, list):
            return []
        return [str(v).strip()[:500] for v in valor if str(v).strip()]

    return {
        'state': estado,
        'reason': (str(dados.get('reason') or '').strip() or None),
        'confidence': confianca,
        'questions': _lista(dados.get('questions')),
        'partial_answers': _lista(dados.get('partial_answers')),
        'commitments': _lista(dados.get('commitments')),
        'deadline_text': prazo_texto,
        'evidence': evidencias,
    }
