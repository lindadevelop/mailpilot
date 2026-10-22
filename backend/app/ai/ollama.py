"""Cliente do Ollama (IA local). Modelo configurável por variável de ambiente."""

import httpx

from ..config import get_settings


class OllamaError(RuntimeError):
    pass


class OllamaClient:
    """Fala com o Ollama local e devolve o texto da resposta.

    `format: 'json'` obriga o modelo a produzir JSON — a validação do conteúdo é
    feita depois, em `validator.py`, porque o formato não garante correção.
    """

    def __init__(self, base_url: str | None = None, model: str | None = None, timeout: float = 120.0):
        settings = get_settings()
        self.base_url = (base_url or settings.ollama_base_url).rstrip('/')
        self.model = model or settings.ollama_model
        self.timeout = timeout

    def disponivel(self) -> bool:
        try:
            resposta = httpx.get(f'{self.base_url}/api/tags', timeout=3.0)
            return resposta.status_code == 200
        except httpx.HTTPError:
            return False

    def classificar(self, system_prompt: str, user_prompt: str) -> str:
        payload = {
            'model': self.model,
            'format': 'json',
            'stream': False,
            'options': {'temperature': 0},
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt},
            ],
        }
        try:
            resposta = httpx.post(f'{self.base_url}/api/chat', json=payload, timeout=self.timeout)
        except httpx.HTTPError as exc:
            raise OllamaError(f'Falha a contactar o Ollama em {self.base_url}: {exc}') from exc

        if resposta.status_code != 200:
            raise OllamaError(f'Ollama respondeu {resposta.status_code}: {resposta.text[:200]}')

        dados = resposta.json()
        texto = (dados.get('message') or {}).get('content') or dados.get('response') or ''
        if not texto.strip():
            raise OllamaError('O Ollama devolveu uma resposta vazia.')
        return texto
