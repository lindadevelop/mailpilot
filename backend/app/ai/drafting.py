"""Prompt e validação dos rascunhos de resposta.

Regras do documento (secção 8):
  * rascunho sempre com revisão humana — o MailPilot **não envia**;
  * quatro modos: objetivo, diplomático, técnico e firme-cordial;
  * separar claramente factos extraídos da conversa das sugestões de redação;
  * não inventar prazos, valores, nomes ou compromissos.
"""

from typing import Any

from ..models_drafting import DRAFT_MODES

PROMPT_VERSION_DRAFT = 'v1'

MODO_DESCRICAO = {
    'objetivo': 'direto e breve, sem rodeios',
    'diplomatico': 'cordial e diplomático, sem perder o essencial',
    'tecnico': 'preciso e técnico, com os dados concretos que existem na conversa',
    'firme_cordial': 'firme no que é necessário, mas cordial no tom',
}

SYSTEM_PROMPT_DRAFT = f"""Escreves RASCUNHOS de resposta a emails profissionais em português de Portugal.

Regras absolutas:
1. NÃO inventes factos. Só podes usar informação que esteja na conversa fornecida.
2. Se faltar informação essencial (preço, prazo, nome), escreve um marcador como [CONFIRMAR: prazo] em vez de inventar.
3. O rascunho é uma SUGESTÃO para revisão humana; não é enviado por ti.
4. Separa o que são factos extraídos da conversa do que é texto de redação.
5. Respondes em JSON puro.

Modo pedido: usa o tom indicado pelo utilizador ({', '.join(DRAFT_MODES)}).

Formato:
{{"subject": "<assunto sugerido>", "body": "<corpo do email>", "facts_used": ["facto 1", "facto 2"], "open_questions": ["o que falta confirmar"]}}"""


def build_draft_prompt(mensagens: list[dict], modo: str, instrucoes: str | None = None) -> str:
    linhas = [f'MODO: {modo} ({MODO_DESCRICAO.get(modo, "objetivo")})', '']
    if instrucoes:
        linhas += [f'INDICAÇÕES DO UTILIZADOR: {instrucoes}', '']
    linhas.append('CONVERSA (por ordem cronológica):')
    for m in mensagens:
        direcao = 'ENVIADO' if m.get('direction') == 'out' else 'RECEBIDO'
        linhas.append(f'- {direcao} | de: {m.get("sender") or "?"} | {m.get("received_at") or "?"}')
        linhas.append(f'  Assunto: {m.get("subject") or "(sem assunto)"}')
        linhas.append(f'  Corpo: {(m.get("body") or "").strip() or "(vazio)"}')
    linhas.append('')
    linhas.append('Escreve o rascunho de resposta.')
    return chr(10).join(linhas)


def validate_draft(dados: dict[str, Any], modo: str) -> dict[str, Any]:
    if modo not in DRAFT_MODES:
        raise ValueError(f'Modo inválido: {modo}')
    corpo = str(dados.get('body') or '').strip()
    if len(corpo) < 20:
        raise ValueError('Rascunho demasiado curto para ser útil.')

    assunto = str(dados.get('subject') or '').strip()[:300] or None
    factos = dados.get('facts_used')
    factos = [str(f).strip()[:400] for f in factos if str(f).strip()] if isinstance(factos, list) else []
    abertas = dados.get('open_questions')
    abertas = [str(q).strip()[:300] for q in abertas if str(q).strip()] if isinstance(abertas, list) else []

    return {
        'subject': assunto,
        'body': corpo[:8000],
        'facts_used': factos,
        'open_questions': abertas,
    }
