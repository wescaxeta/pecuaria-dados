import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Connection, Engine, create_engine, text

from pecuaria_dados import transformacao
from pecuaria_dados.api import app, obter_conexao
from pecuaria_dados.carga import carregar
from tests.dados import EFETIVO_GO, MUNICIPIOS_GO

RAIZ = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def engine_teste() -> Iterator[Engine]:
    """PostgreSQL real, recriado do zero e migrado com o Alembic (as migrations também são testadas)."""
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Defina TEST_DATABASE_URL para rodar os testes com banco.")

    engine = create_engine(url)
    with engine.begin() as conexao:
        conexao.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public;"))

    config = Config(str(RAIZ / "alembic.ini"))
    config.attributes["database_url"] = url
    command.upgrade(config, "head")

    yield engine
    engine.dispose()


@pytest.fixture
def conexao(engine_teste: Engine) -> Iterator[Connection]:
    with engine_teste.connect() as conexao:
        conexao.execute(text("TRUNCATE efetivo_rebanho, municipio"))
        conexao.commit()
        yield conexao


@pytest.fixture
def dados_carregados(conexao: Connection) -> Connection:
    carregar(conexao, transformacao.municipios(MUNICIPIOS_GO), transformacao.efetivo_rebanhos(EFETIVO_GO))
    return conexao


@pytest.fixture
def cliente(dados_carregados: Connection) -> Iterator[TestClient]:
    app.dependency_overrides[obter_conexao] = lambda: dados_carregados
    with TestClient(app) as cliente:
        yield cliente
    app.dependency_overrides.clear()
