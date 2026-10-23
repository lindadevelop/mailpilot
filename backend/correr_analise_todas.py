"""Classifica todas as conversas sem análise, com progresso visível no log."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import select

from app.ai.ollama import OllamaClient, OllamaError
from app.db import SessionLocal, init_db
from app.models import Conversation
from app.models_analysis import AiAnalysis
from app.services import analysis_service


def main() -> int:
    init_db()
    db = SessionLocal()
    try:
        cliente = OllamaClient()
        if not cliente.disponivel():
            print('!! Ollama indisponível em', cliente.base_url, flush=True)
            return 2
        print(f'Modelo: {cliente.model} | base: {cliente.base_url}', flush=True)

        analisadas = set(db.scalars(select(AiAnalysis.conversation_id)).all())
        conversas = db.scalars(select(Conversation).order_by(Conversation.id)).all()
        pendentes = [c for c in conversas if c.id not in analisadas]
        print(f'Conversas: {len(conversas)} | já analisadas: {len(analisadas)} | a fazer: {len(pendentes)}', flush=True)

        inicio = time.time()
        feitas = falhadas = 0
        for i, conversa in enumerate(pendentes, 1):
            t0 = time.time()
            try:
                resultado = analysis_service.analisar_conversa(db, conversa, cliente, cliente.model)
                aplicado = bool(resultado.get('aplicado'))
                feitas += 1 if aplicado else 0
                falhadas += 0 if aplicado else 1
                detalhe = resultado.get('state') or resultado.get('motivo') or resultado
                print(
                    f'[{i}/{len(pendentes)}] conv {conversa.id} «{(conversa.subject or "")[:40]}» -> '
                    f'{"OK" if aplicado else "RECUSADO"}: {str(detalhe)[:160]} ({time.time() - t0:.1f}s)',
                    flush=True,
                )
            except (OllamaError, ValueError) as exc:
                falhadas += 1
                print(f'[{i}/{len(pendentes)}] conv {conversa.id} ERRO: {type(exc).__name__}: {exc}', flush=True)
        print(f'FIM: {feitas} classificadas, {falhadas} não, em {(time.time() - inicio) / 60:.1f} min', flush=True)
        return 0
    finally:
        db.close()


if __name__ == '__main__':
    raise SystemExit(main())
