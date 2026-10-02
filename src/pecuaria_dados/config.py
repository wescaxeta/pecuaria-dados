from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Configuracao(BaseSettings):
    """Configuração por variáveis de ambiente (ou arquivo .env)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://pecuaria:pecuaria@localhost:5432/pecuaria"
    sidra_url: str = "https://apisidra.ibge.gov.br"
    localidades_url: str = "https://servicodados.ibge.gov.br/api/v1/localidades"
    http_timeout_segundos: float = 60.0
    http_tentativas: int = 4


@lru_cache
def configuracao() -> Configuracao:
    return Configuracao()
