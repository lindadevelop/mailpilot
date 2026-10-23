"""Remetentes na lista e resumo por assunto."""

from fastapi.testclient import TestClient

from app.api.routes import BatchIn
from app.main import app
from app.services import reports_service

CABECALHO = {'X-API-Key': 'chave-de-teste'}


def test_normalizar_assunto_remove_prefixos():
    for variante in ('Re: Proposta', 'RE: Proposta', 'Re: RE: Fwd: Proposta', 'Enc: Proposta', 'Res: Proposta'):
        assert reports_service.normalizar_assunto(variante) == 'Proposta'


def test_normalizar_assunto_sem_assunto():
    assert reports_service.normalizar_assunto(None) == '(sem assunto)'
    assert reports_service.normalizar_assunto('   ') == '(sem assunto)'


def test_assunto_sem_prefixo_fica_igual():
    assert reports_service.normalizar_assunto('Orçamento frigorífico') == 'Orçamento frigorífico'


def _mensagem(external_id, conversation_external_id, subject, sender, direction='in', is_read=False):
    return {
        'external_id': external_id,
        'conversation_external_id': conversation_external_id,
        'direction': direction,
        'sender': sender,
        'recipients': ['compras@empresa.pt'],
        'subject': subject,
        'body': 'Bom dia, podem enviar proposta até sexta-feira?',
        'received_at': '2026-10-20T09:30:00',
        'is_read': is_read,
    }


def _importar(payload):
    with TestClient(app) as cliente:
        return cliente.post('/api/emails/batch', json=payload, headers=CABECALHO)


def test_listagem_traz_remetente(payload_factory):
    from app.db import SessionLocal
    from app.services import import_service

    db = SessionLocal()
    try:
        import_service.import_batch(db, payload_factory(['id-1'], conversation_external_id='conv-rem'))
    finally:
        db.close()
    with TestClient(app) as cliente:
        corpo = cliente.get('/api/conversations', headers=CABECALHO).json()
    assert corpo['items'], 'sem conversas na listagem'
    item = corpo['items'][0]
    assert item['sender'], 'a listagem não traz quem enviou'
    assert item['last_direction'] in ('in', 'out')


def test_resumo_agrupa_o_mesmo_tema(payload_factory):
    from app.db import SessionLocal
    from app.services import import_service

    db = SessionLocal()
    try:
        # Dois fios diferentes com o mesmo tema, escritos por pessoas diferentes.
        import_service.import_batch(db, BatchIn(**{
            'account_email': 'compras@empresa.pt', 'source': 'grok',
            'messages': [_mensagem('t-1', 'conv-tema-a', 'Proposta de equipamento', 'ana@cliente.pt')],
        }))
        import_service.import_batch(db, BatchIn(**{
            'account_email': 'compras@empresa.pt', 'source': 'grok',
            'messages': [_mensagem('t-2', 'conv-tema-b', 'RE: Proposta de equipamento', 'rui@outro.pt')],
        }))
    finally:
        db.close()
    with TestClient(app) as cliente:
        corpo = cliente.get('/api/reports/subjects', headers=CABECALHO).json()

    tema = next(i for i in corpo['items'] if i['assunto'] == 'Proposta de equipamento')
    assert tema['conversas'] >= 2, 'os fios com Re: não foram agrupados no mesmo tema'
    assert set(tema['remetentes']) >= {'ana@cliente.pt', 'rui@outro.pt'}
    assert 'RE: Proposta de equipamento' in tema['variantes']


def test_resumo_traz_estado_do_tema(payload_factory):
    from app.db import SessionLocal
    from app.services import import_service

    db = SessionLocal()
    try:
        import_service.import_batch(db, BatchIn(**{
            'account_email': 'compras@empresa.pt', 'source': 'grok',
            'messages': [_mensagem('t-3', 'conv-tema-c', 'Proposta de equipamento', 'ana@cliente.pt')],
        }))
    finally:
        db.close()
    with TestClient(app) as cliente:
        corpo = cliente.get('/api/reports/subjects', headers=CABECALHO).json()
    tema = next(i for i in corpo['items'] if i['assunto'] == 'Proposta de equipamento')
    assert tema['estado'] in {'Indeterminado', 'Preciso responder', 'Em análise'}
    assert tema['mensagens'] >= 1
    assert isinstance(tema['conversation_ids'], list) and tema['conversation_ids']
