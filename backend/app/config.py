"""Configuração por variáveis de ambiente (ver .env.example)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='../.env', extra='ignore')

    app_env: str = 'development'
    database_url: str = 'sqlite:///./data/mailpilot.db'
    api_key: str = 'muda-esta-chave'
    log_level: str = 'info'

    ollama_base_url: str = 'http://127.0.0.1:11434'
    ollama_model: str = 'qwen2.5:7b'

    mcp_enabled: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
