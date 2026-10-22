"""Ponto de entrada da API do MailPilot AI."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router
from .api.routes_analysis import router as analysis_router
from .config import get_settings
from .db import init_db

# Logs sem conteúdo de email (dados empresariais): só nível e mensagem.
logging.basicConfig(level=get_settings().log_level.upper(), format='%(levelname)s %(message)s')


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title='MailPilot AI',
    description='Gestão inteligente de email profissional: pendências, prazos e compromissos.',
    version='0.1.0',
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:5173', 'http://127.0.0.1:5173'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(router)
app.include_router(analysis_router)
