"""Prompt e validação para preferências de comunicação e hipótese DISC.

Regras do documento que estão aqui codificadas:
  * observar apenas o que se vê nas mensagens profissionais (formalidade,
    concisão, pedidos de detalhe, referências a prazos, orientações explícitas);
  * hipótese D/I/S/C/combinação/Indeterminado, com confiança e citações;
  * nunca inferir características sensíveis nem produzir diagnóstico;
  * sem evidência suficiente → "Indeterminado".
"""

from typing import Any

from ..models_communication import DISC_HYPOTHESES
from .validator import MIN_QUOTE_CHARS, _normalizar

PROMPT_VERSION_COM = 'v1'

ASPECTOS = ('formalidade', 'concisao', 'prazos', 'pedidos', 'disc')

SYSTEM_PROMPT_COM = f"""Analisas o ESTILO DE COMUNICAÇÃO observável de um contacto em emails profissionais (português de Portugal).

Isto NÃO é um teste de personalidade e NÃO é um diagnóstico. Descreve apenas o que está escrito.

Observa: formalidade, concisão, pedidos de detalhe, referências a prazos, orientações explícitas e preferências declaradas.
NUNCA inferas idade, sexo, saúde, origem étnica, religião, orientação sexual, opiniões políticas, estado familiar ou qualquer característica sensível. Não emitas juízos de desempenho.

Hipótese DISC permitida (uma): {', '.join(DISC_HYPOTHESES)}. Usa "Indeterminado" quando não houver evidência suficiente.

Responde APENAS com JSON:
{{
  "formality": "formal" | "informal" | "Indeterminado",
  "concise": true|false|null,
  "prefers_detail": true|false|null,
  "mentions_deadlines": true|false|null,
  "explicit_requests": true|false|null,
  "disc_hypothesis": "<uma das hipóteses>",
  "disc_confidence": <0.0 a 1.0>,
  "reason": "<justificação curta, em português, sobre o que se observa>",
  "evidence": [{{"message_id": <id>, "quote": "<excerto literal>", "aspect": "formalidade|concisao|prazos|pedidos|disc"}}]
}}"""


def build_contact_prompt(mensagens: list[dict]) -> str:
    linhas = ['MENSAGENS DESTE CONTACTO (por ordem cronológica):', '']
    for m in mensagens:
        corpo = (m.get('body') or '').strip()
        linhas.append(f'[message_id={m.get("id")}] {m.get("received_at") or m.get("sent_at") or "?"}')
        linhas.append(f'Assunto: {m.get("subject") or "(sem assunto)"}')
        linhas.append(f'Corpo: {corpo if corpo else "(vazio)"}')
        linhas.append('---')
    linhas.append('Descreve o estilo de comunicação observável e a hipótese DISC.')
    return chr(10).join(linhas)


def validate_communication(dados: dict[str, Any], mensagens: dict[int, str]) -> dict[str, Any]:
    """Valida a resposta. Citações têm de ser literais; hipótese tem de ser da lista."""
    hipotese = str(dados.get('disc_hypothesis', '')).strip()
    if hipotese not in DISC_HYPOTHESES:
        raise ValueError(f'Hipótese DISC inválida: {hipotese!r}')

    confianca = dados.get('disc_confidence', 0.0)
    try:
        confianca = float(confianca)
    except (TypeError, ValueError):
        raise ValueError('Confiança não numérica.')
    if not 0.0 <= confianca <= 1.0:
        raise ValueError('Confiança fora do intervalo 0..1.')

    formalidade = str(dados.get('formality', 'Indeterminado')).strip()
    if formalidade not in ('formal', 'informal', 'Indeterminado'):
        formalidade = 'Indeterminado'

    def _tri(valor: Any) -> bool | None:
        return valor if isinstance(valor, bool) else None

    evidencias: list[dict[str, Any]] = []
    for item in dados.get('evidence') or []:
        if not isinstance(item, dict):
            continue
        try:
            mid = int(item.get('message_id'))
        except (TypeError, ValueError):
            continue
        if mid not in mensagens:
            raise ValueError(f'Evidência fora do contacto: message_id {mid}')
        quote = (item.get('quote') or '').strip()
        if len(quote) < MIN_QUOTE_CHARS or _normalizar(quote) not in _normalizar(mensagens[mid]):
            raise ValueError(f'Citação não literal na mensagem {mid}: {quote!r}')
        aspecto = str(item.get('aspect') or 'disc').strip()
        evidencias.append({'message_id': mid, 'quote': quote[:1000],
                           'aspect': aspecto if aspecto in ASPECTOS else 'disc'})

    # Sem qualquer citação não há perfil: evita «personalidade inventada».
    if not evidencias:
        raise ValueError('Sem citações: não é possível descrever o estilo de comunicação.')

    return {
        'formality': formalidade,
        'concise': _tri(dados.get('concise')),
        'prefers_detail': _tri(dados.get('prefers_detail')),
        'mentions_deadlines': _tri(dados.get('mentions_deadlines')),
        'explicit_requests': _tri(dados.get('explicit_requests')),
        'disc_hypothesis': hipotese,
        'disc_confidence': round(confianca, 2),
        'reason': (str(dados.get('reason') or '').strip() or None),
        'evidence': evidencias,
    }
