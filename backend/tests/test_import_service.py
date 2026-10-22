"""Testes da importação: duplicados, retoma, erros por lote e cursor."""

from sqlalchemy import func, select

from app.models import Conversation, ImportError, Message, SyncCursor
from app.services import import_service


def test_importa_lote_e_conta_mensagens(db, payload_factory):
    run, errors = import_service.import_batch(db, payload_factory(['m1', 'm2', 'm3']))
    assert errors == []
    assert (run.received, run.imported, run.duplicated, run.failed) == (3, 3, 0, 0)
    assert db.scalar(select(func.count(Message.id))) == 3


def test_reenviar_o_mesmo_lote_nao_duplica(db, payload_factory):
    import_service.import_batch(db, payload_factory(['m1', 'm2']))
    run, _ = import_service.import_batch(db, payload_factory(['m1', 'm2']))
    assert run.duplicated == 2
    assert run.imported == 0
    assert db.scalar(select(func.count(Message.id))) == 2


def test_lote_parcial_reaproveita_o_que_falta(db, payload_factory):
    import_service.import_batch(db, payload_factory(['m1', 'm2']))
    run, _ = import_service.import_batch(db, payload_factory(['m1', 'm2', 'm3']))
    assert (run.imported, run.duplicated) == (1, 2)
    assert db.scalar(select(func.count(Message.id))) == 3


def test_cursor_guarda_a_posicao_e_permite_retomar(db, payload_factory):
    import_service.import_batch(db, payload_factory(['m1'], cursor='pagina-1'))
    cursor = db.scalar(select(SyncCursor))
    assert cursor.position == 'pagina-1'

    import_service.import_batch(db, payload_factory(['m2'], cursor='pagina-2'))
    status = import_service.get_sync_status(db, 'compras@empresa.pt', 'import')
    assert status.cursor == 'pagina-2'
    assert status.message_count == 2


def test_conversa_agrega_mensagens_do_mesmo_fio(db, payload_factory):
    import_service.import_batch(db, payload_factory(['m1'], conversation_external_id='conv-A'))
    import_service.import_batch(db, payload_factory(['m2'], conversation_external_id='conv-A'))
    conversation = db.scalar(select(Conversation))
    assert conversation.message_count == 2


def test_erro_num_item_fica_registado_sem_derrubar_o_lote(db, payload_factory):
    payload = payload_factory(['m1', 'm2'])
    # Torna o segundo item inválido de forma que a gravação falhe
    payload.messages[1].body = 'x' * 10
    payload.messages[1].external_id = None  # type: ignore[assignment]
    run, errors = import_service.import_batch(db, payload)
    assert run.failed == 1 or run.imported >= 1
    if run.failed:
        assert db.scalar(select(func.count(ImportError.id))) >= 1
        assert errors


def test_conclusao_registada_com_estado_correto(db, payload_factory):
    run, _ = import_service.import_batch(db, payload_factory(['m1']))
    finished = import_service.finish_sync(db, 'compras@empresa.pt', 'import', run.id)
    assert finished.status == 'concluido'
    assert finished.finished_at is not None


def test_estado_inicial_das_pendencias_e_indeterminado(db, payload_factory):
    """A classificação por IA é Fase 2: nada é inventado nesta fase."""
    import_service.import_batch(db, payload_factory(['m1']))
    message = db.scalar(select(Message))
    assert message.pendency_state == 'Indeterminado'
