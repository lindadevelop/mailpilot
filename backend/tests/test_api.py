"""Testes dos endpoints (sem base de dados externa)."""

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault('API_KEY', 'chave-de-teste')


@pytest.fixture()
def client(tmp_path, monkeypatch):
    # Base de dados própria por teste (ficheiro, porque a API abre as suas sessões)
    db_file = tmp_path / 'teste.db'
    monkeypatch.setenv('DATABASE_URL', f'sqlite:///{db_file.as_posix()}')
    monkeypatch.setenv('API_KEY', 'chave-de-teste')

    from app import config, db as db_module

    config.get_settings.cache_clear()
    db_module.engine.dispose()
    db_module.engine = db_module.make_engine(os.environ['DATABASE_URL'])
    db_module.SessionLocal.configure(bind=db_module.engine)

    from app.main import app

    with TestClient(app) as c:
        yield c

    db_module.engine.dispose()


def test_health(client):
    r = client.get('/health')
    assert r.status_code == 200
    assert r.json()['status'] == 'ok'


def test_batch_exige_chave(client):
    r = client.post('/api/emails/batch', json={'account_email': 'a@b.pt', 'messages': []})
    assert r.status_code == 401


def test_batch_importa_e_dashboard_reflete(client):
    body = {
        'account_email': 'compras@empresa.pt',
        'source': 'import',
        'cursor': 'p1',
        'messages': [
            {
                'external_id': 'e1',
                'subject': 'Orçamento',
                'sender': 'cliente@exemplo.pt',
                'recipients': ['compras@empresa.pt'],
                'body': 'Podem enviar proposta?',
                'received_at': '2026-10-20T09:30:00',
                'conversation_external_id': 'conv-1',
            }
        ],
    }
    headers = {'X-API-Key': 'chave-de-teste'}
    r = client.post('/api/emails/batch', json=body, headers=headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert (data['imported'], data['duplicated']) == (1, 0)

    # Reenviar não duplica (idempotência ponta-a-ponta)
    again = client.post('/api/emails/batch', json=body, headers=headers).json()
    assert again['duplicated'] == 1 and again['imported'] == 0

    status = client.get('/api/sync/status?account_email=compras@empresa.pt', headers=headers).json()
    assert status['cursor'] == 'p1'
    assert status['message_count'] == 1

    dash = client.get('/api/dashboard', headers=headers).json()
    assert dash['total_messages'] == 1
    assert dash['unread_messages'] == 1

    convs = client.get('/api/conversations', headers=headers).json()
    assert convs['total'] == 1
