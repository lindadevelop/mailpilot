"""Corre o classificador da Fase 2 contra o Ollama real, sobre a base de dados local.

Feito por script (e não por HTTP) para não depender de reiniciar o servidor: prova
a integração real com a IA local, gravando análise, evidências e estado.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.ai.ollama import OllamaClient  # noqa: E402
from app.db import SessionLocal, init_db  # noqa: E402
from app.services import analysis_service  # noqa: E402


def main() -> int:
    init_db()
    db = SessionLocal()
    cliente = OllamaClient()

    if not cliente.disponivel():
        print('Ollama indisponível — nada a fazer.')
        return 1
    print(f'Modelo: {cliente.model}')

    pendentes = analysis_service.conversas_a_analisar(db, limite=3)
    print(f'Conversas a analisar: {[c.id for c in pendentes]}')
    if not pendentes:
        print('Sem conversas novas para analisar.')
        return 0

    resultado = analysis_service.run_analysis(db, cliente, limite=3, model_name=cliente.model)
    print(f"Analisadas: {resultado['analisadas']} | ignoradas: {resultado['ignoradas']}")
    for r in resultado['resultados']:
        print('  ', r)

    from app.models_analysis import AiAnalysis, AiAnalysisEvidence  # noqa: E402

    analise = db.query(AiAnalysis).order_by(AiAnalysis.id.desc()).first()
    if analise:
        evidencias = db.query(AiAnalysisEvidence).filter_by(analysis_id=analise.id).all()
        print('--- guardado na base de dados ---')
        print(f'estado: {analise.state} | confiança: {analise.confidence} | modelo: {analise.model}')
        print(f'motivo: {analise.reason}')
        print(f'prazo (só se explícito): {analise.deadline_text}')
        print(f'evidências: {[(e.message_id, (e.quote or "")[:60]) for e in evidencias]}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
