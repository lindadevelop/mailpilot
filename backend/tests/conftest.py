import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import Base  # noqa: E402
from app import models  # noqa: E402,F401


@pytest.fixture()
def db():
    engine = create_engine('sqlite:///:memory:', connect_args={'check_same_thread': False}, future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)
    session = Session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def payload_factory():
    from app.schemas import BatchIn

    def make(external_ids, account='compras@empresa.pt', source='import', cursor=None, **extra):
        messages = [
            {
                'external_id': ext,
                'subject': extra.get('subject', 'Pedido de orçamento'),
                'sender': extra.get('sender', 'cliente@exemplo.pt'),
                'recipients': extra.get('recipients', ['compras@empresa.pt']),
                'body': extra.get('body', 'Podem enviar proposta até sexta-feira?'),
                'received_at': extra.get('received_at', '2026-10-20T09:30:00'),
                'conversation_external_id': extra.get('conversation_external_id', 'conv-1'),
            }
            for ext in external_ids
        ]
        return BatchIn(account_email=account, source=source, messages=messages, cursor=cursor)

    return make
