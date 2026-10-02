"""Carga e API contra PostgreSQL real (pulados sem TEST_DATABASE_URL)."""

from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Connection, text

from pecuaria_dados import transformacao
from pecuaria_dados.carga import carregar
from tests.dados import BOVINO, EFETIVO_GO, MUNICIPIOS_GO, linha_sidra

pytestmark = pytest.mark.banco


def _contar(conexao: Connection) -> int:
    return int(conexao.execute(text("SELECT count(*) FROM efetivo_rebanho")).scalar_one())


def test_carga_e_idempotente_e_atualiza_valores(dados_carregados: Connection) -> None:
    corrigido = [
        linha_sidra(5200001, 2025, BOVINO, "250")
        if (r["D1C"], r["D3C"], r["D4C"]) == ("5200001", "2025", BOVINO)
        else r
        for r in EFETIVO_GO
    ]

    carregar(
        dados_carregados, transformacao.municipios(MUNICIPIOS_GO), transformacao.efetivo_rebanhos(corrigido)
    )

    assert _contar(dados_carregados) == len(EFETIVO_GO)
    valor = dados_carregados.execute(
        text(
            "SELECT efetivo FROM efetivo_rebanho"
            " WHERE municipio_codigo = 5200001 AND ano = 2025 AND especie = 'bovino'"
        )
    ).scalar_one()
    assert valor == 250


def test_valores_sigilosos_ficam_nulos(dados_carregados: Connection) -> None:
    linha = dados_carregados.execute(
        text("SELECT efetivo, situacao FROM efetivo_rebanho WHERE especie = 'caprino'")
    ).one()

    assert linha.efetivo is None
    assert linha.situacao == "sigiloso"


def test_metadados(cliente: TestClient) -> None:
    corpo = cliente.get("/metadados").json()

    assert corpo["ufs"] == ["GO"]
    assert corpo["anos"] == [2024, 2025]


def test_ranking_com_posicao_e_participacao(cliente: TestClient) -> None:
    resposta = cliente.get("/ufs/go/ranking", params={"especie": "bovino", "limite": 2})

    assert resposta.status_code == 200
    # 2025 (ano mais recente): 600 + 400 + 200 = 1.200 cabeças
    assert resposta.json() == [
        {
            "posicao": 1,
            "codigo": 5200002,
            "nome": "Rio Verde",
            "efetivo": 600,
            "participacao_percentual": 50.0,
        },
        {"posicao": 2, "codigo": 5200003, "nome": "Jataí", "efetivo": 400, "participacao_percentual": 33.33},
    ]


def test_evolucao_calcula_variacao_sobre_o_ano_anterior(cliente: TestClient) -> None:
    corpo = cliente.get("/ufs/GO/evolucao", params={"especie": "bovino"}).json()

    assert corpo == [
        {"ano": 2024, "efetivo": 1000, "variacao_absoluta": None, "variacao_percentual": None},
        {"ano": 2025, "efetivo": 1200, "variacao_absoluta": 200, "variacao_percentual": 20.0},
    ]


def test_resumo_ignora_valores_nao_disponiveis(cliente: TestClient) -> None:
    corpo: list[dict[str, Any]] = cliente.get("/ufs/GO/resumo", params={"ano": 2025}).json()
    suinos = next(item for item in corpo if item["especie"] == "suino")

    # 0 (zero absoluto) + 50; o "..." não entra na soma
    assert suinos["efetivo_total"] == 50
    assert suinos["municipios_com_rebanho"] == 1


def test_busca_de_municipio_ignora_acentos(cliente: TestClient) -> None:
    corpo = cliente.get("/municipios", params={"nome": "goiania"}).json()

    assert [m["nome"] for m in corpo] == ["Goiânia"]


def test_rebanhos_do_municipio_no_ano_mais_recente(cliente: TestClient) -> None:
    corpo = cliente.get("/municipios/5200002/rebanhos").json()

    assert corpo["ano"] == 2025
    assert [r["especie"] for r in corpo["rebanhos"]] == ["bovino", "suino", "caprino"]


@pytest.mark.parametrize(
    ("url", "status"),
    [
        pytest.param("/ufs/XX/ranking", 422, id="UF inexistente"),
        pytest.param("/ufs/GO/ranking?especie=gato", 422, id="espécie inválida"),
        pytest.param("/ufs/GO/ranking?ano=1990", 404, id="ano não carregado"),
        pytest.param("/municipios/1/rebanhos", 404, id="município inexistente"),
    ],
)
def test_erros(cliente: TestClient, url: str, status: int) -> None:
    assert cliente.get(url).status_code == status
