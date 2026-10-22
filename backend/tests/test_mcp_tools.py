"""Ferramentas MCP: mesmas garantias da API (idempotência, cursores, erros)."""

from sqlalchemy import func, select

from app.models import Message
from app.mcp import tools


def _msg(ext: str, **over):
    base = {
        'external_id': ext,
        'subject': 'Pedido de proposta',
        'sender': 'cliente@exemplo.pt',
        'recipients': ['compras@empresa.pt'],
        'body': 'Podem enviar proposta até sexta-feira?',
        'received_at': '2026-10-20T09:30:00',
        'conversation_external_id': 'conv-mcp',
    }
    base.update(over)
    return base


def test_import_emails_importa_e_e_idempotente(db):
    primeiro = tools.import_emails(db, 'compras@empresa.pt', [_msg('g1'), _msg('g2')], source='grok')
    assert primeiro['ok'] is True
    assert (primeiro['imported'], primeiro['duplicated']) == (2, 0)

    # O Grok reenvia o mesmo lote: não duplica
    segundo = tools.import_emails(db, 'compras@empresa.pt', [_msg('g1'), _msg('g2')], source='grok')
    assert (segundo['imported'], segundo['duplicated']) == (0, 2)
    assert db.scalar(select(func.count(Message.id))) == 2


def test_import_emails_recusa_payload_invalido(db):
    assert tools.import_emails(db, 'sem-arroba', [_msg('g1')])['ok'] is False
    assert tools.import_emails(db, 'compras@empresa.pt', [])['ok'] is False
    invalido = tools.import_emails(db, 'compras@empresa.pt', [{'external_id': ''}])
    assert invalido['ok'] is False
    assert 'payload inválido' in invalido['error']


def test_get_sync_cursor_devolve_posicao(db):
    tools.import_emails(db, 'compras@empresa.pt', [_msg('g1')], source='grok', cursor='cursor-42')
    resultado = tools.get_sync_cursor(db, 'compras@empresa.pt', 'grok')
    assert resultado['ok'] is True
    assert resultado['cursor'] == 'cursor-42'
    assert resultado['message_count'] == 1


def test_finish_sync_conclui_a_execucao(db):
    lote = tools.import_emails(db, 'compras@empresa.pt', [_msg('g1')], source='grok')
    fim = tools.finish_sync(db, 'compras@empresa.pt', 'grok', lote['sync_run_id'], 'fim do historico')
    assert fim['ok'] is True
    assert fim['status'] == 'concluido'
    assert fim['imported'] == 1


def test_finish_sync_com_execucao_inexistente(db):
    assert tools.finish_sync(db, 'nao-existe@empresa.pt', 'grok')['ok'] is False


def test_get_import_errors_devolve_erros(db):
    # Cria um erro de importação diretamente (o caminho real exige falha de gravação)
    from app.models import Account, ImportError

    conta = Account(name='x', email_address='erros@empresa.pt', source='grok')
    db.add(conta)
    db.flush()
    db.add(ImportError(account_id=conta.id, external_id='mau-1', reason='data inválida'))
    db.commit()

    resultado = tools.get_import_errors(db, limit=5)
    assert resultado['ok'] is True
    assert resultado['total'] >= 1
    assert any(e['external_id'] == 'mau-1' for e in resultado['errors'])


def test_ferramentas_nao_enviam_nem_apagam_mensagens(db):
    """Só importação e leitura: nenhuma ferramenta exposta muda o conteúdo."""
    import inspect

    nomes = [n for n, f in inspect.getmembers(tools, inspect.isfunction) if not n.startswith('_')]
    proibidos = [n for n in nomes if any(p in n for p in ('send', 'delete', 'move', 'purge'))]
    assert proibidos == []
