"""Sessão e motor de base de dados (SQLite no MVP, pronto para PostgreSQL)."""

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import get_settings


class Base(DeclarativeBase):
    pass


def _prepare_sqlite_path(url: str) -> None:
    """O SQLite não cria diretórios: sem isto, a primeira escrita falha."""
    prefix = 'sqlite:///'
    if url.startswith(prefix):
        db_path = Path(url[len(prefix):])
        db_path.parent.mkdir(parents=True, exist_ok=True)


def make_engine(url: str | None = None):
    url = url or get_settings().database_url
    _prepare_sqlite_path(url)
    connect_args = {'check_same_thread': False} if url.startswith('sqlite') else {}
    return create_engine(url, connect_args=connect_args, future=True)


engine = make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


def init_db() -> None:
    from . import models  # noqa: F401  (registar as tabelas)
    from . import models_analysis  # noqa: F401  (Fase 2)
    from . import models_communication  # noqa: F401  (Fase 4)

    Base.metadata.create_all(bind=engine)
