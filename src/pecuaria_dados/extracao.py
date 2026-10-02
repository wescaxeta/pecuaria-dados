"""Extração das APIs públicas do IBGE: SIDRA (dados da pesquisa) e Localidades (municípios)."""

import logging
from typing import Any, Self

import httpx
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from pecuaria_dados.config import Configuracao
from pecuaria_dados.dominio import CODIGOS_SIDRA, codigo_uf

logger = logging.getLogger(__name__)

TABELA_PPM = 3939  # Pesquisa da Pecuária Municipal: efetivo dos rebanhos
VARIAVEL_EFETIVO = 105
CLASSIFICACAO_TIPO_REBANHO = 79


class ErroExtracao(RuntimeError):
    """A API do IBGE respondeu fora do esperado ou ficou indisponível após as tentativas."""


def _falha_transitoria(erro: BaseException) -> bool:
    """Rede, timeout e erros 5xx podem passar sozinhos; 4xx indica requisição errada."""
    if isinstance(erro, httpx.TransportError):
        return True
    return isinstance(erro, httpx.HTTPStatusError) and erro.response.status_code >= 500  # noqa: PLR2004


class ClienteIbge:
    """Cliente HTTP das APIs do IBGE, com timeout e novas tentativas com backoff exponencial."""

    def __init__(self, config: Configuracao, transporte: httpx.BaseTransport | None = None) -> None:
        self._config = config
        self._http = httpx.Client(
            timeout=config.http_timeout_segundos,
            transport=transporte,
            headers={"Accept": "application/json", "User-Agent": "pecuaria-dados (projeto de portfolio)"},
            follow_redirects=True,
        )
        self._get = retry(
            retry=retry_if_exception(_falha_transitoria),
            stop=stop_after_attempt(config.http_tentativas),
            wait=wait_exponential(multiplier=0.5, max=10),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True,
        )(self._get_uma_vez)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        self._http.close()

    def municipios(self, uf: str) -> list[dict[str, Any]]:
        dados = self._get_json(f"{self._config.localidades_url}/estados/{uf.upper()}/municipios")
        return [{"codigo": int(m["id"]), "nome": str(m["nome"]), "uf": uf.upper()} for m in dados]

    def efetivo_rebanhos(self, uf: str, ultimos_anos: int) -> list[dict[str, Any]]:
        """Efetivo de todos os tipos de rebanho, por município da UF, nos últimos N anos publicados."""
        categorias = ",".join(CODIGOS_SIDRA)
        caminho = (
            f"/values/t/{TABELA_PPM}/n6/in%20n3%20{codigo_uf(uf)}/v/{VARIAVEL_EFETIVO}"
            f"/p/last%20{ultimos_anos}/c{CLASSIFICACAO_TIPO_REBANHO}/{categorias}/f/c"
        )
        dados = self._get_json(self._config.sidra_url + caminho)

        # A primeira linha da resposta do SIDRA é o cabeçalho com a descrição das colunas
        return dados[1:]

    def _get_json(self, url: str) -> list[dict[str, Any]]:
        try:
            resposta = self._get(url)
        except httpx.HTTPError as erro:
            raise ErroExtracao(f"Falha ao consultar o IBGE: {erro}") from erro

        dados = resposta.json()
        if not isinstance(dados, list):
            raise ErroExtracao(f"Resposta inesperada do IBGE em {url}: esperava uma lista JSON.")
        return dados

    def _get_uma_vez(self, url: str) -> httpx.Response:
        resposta = self._http.get(url)
        resposta.raise_for_status()
        return resposta
