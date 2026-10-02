import httpx
import pytest
import respx

from pecuaria_dados.config import Configuracao
from pecuaria_dados.etl import main
from pecuaria_dados.extracao import ClienteIbge, ErroExtracao
from tests.dados import CABECALHO_SIDRA, EFETIVO_GO

CONFIG = Configuracao(
    sidra_url="https://sidra.test", localidades_url="https://localidades.test", http_tentativas=3
)
URL_SIDRA_GO = (
    "https://sidra.test/values/t/3939/n6/in%20n3%2052/v/105/p/last%202"
    "/c79/2670,2675,2672,32794,32795,2681,2677,32796,32793,2680/f/c"
)


@pytest.fixture(autouse=True)
def sem_espera(monkeypatch: pytest.MonkeyPatch) -> None:
    """Zera o backoff do tenacity para os testes de retry não esperarem segundos."""
    monkeypatch.setattr("tenacity.nap.time.sleep", lambda _: None)


@respx.mock
def test_monta_a_consulta_do_sidra_e_descarta_o_cabecalho() -> None:
    rota = respx.get(URL_SIDRA_GO).respond(json=[CABECALHO_SIDRA, *EFETIVO_GO])

    with ClienteIbge(CONFIG) as ibge:
        registros = ibge.efetivo_rebanhos("go", ultimos_anos=2)

    assert rota.called
    assert registros == EFETIVO_GO


@respx.mock
def test_busca_municipios_pela_sigla() -> None:
    respx.get("https://localidades.test/estados/GO/municipios").respond(
        json=[{"id": 5208707, "nome": "Goiânia"}, {"id": 5218805, "nome": "Rio Verde"}]
    )

    with ClienteIbge(CONFIG) as ibge:
        municipios = ibge.municipios("go")

    assert municipios == [
        {"codigo": 5208707, "nome": "Goiânia", "uf": "GO"},
        {"codigo": 5218805, "nome": "Rio Verde", "uf": "GO"},
    ]


@respx.mock
def test_repete_apos_erro_5xx_e_queda_de_conexao() -> None:
    rota = respx.get(URL_SIDRA_GO).mock(
        side_effect=[
            httpx.Response(503),
            httpx.ConnectError("conexão recusada"),
            httpx.Response(200, json=[CABECALHO_SIDRA, *EFETIVO_GO]),
        ]
    )

    with ClienteIbge(CONFIG) as ibge:
        registros = ibge.efetivo_rebanhos("GO", ultimos_anos=2)

    assert rota.call_count == 3
    assert len(registros) == len(EFETIVO_GO)


@respx.mock
def test_desiste_apos_o_limite_de_tentativas() -> None:
    rota = respx.get(URL_SIDRA_GO).respond(503)

    with ClienteIbge(CONFIG) as ibge, pytest.raises(ErroExtracao):
        ibge.efetivo_rebanhos("GO", ultimos_anos=2)

    assert rota.call_count == CONFIG.http_tentativas


@respx.mock
def test_erro_4xx_nao_e_repetido() -> None:
    rota = respx.get(URL_SIDRA_GO).respond(400)

    with ClienteIbge(CONFIG) as ibge, pytest.raises(ErroExtracao):
        ibge.efetivo_rebanhos("GO", ultimos_anos=2)

    assert rota.call_count == 1


@respx.mock
def test_resposta_que_nao_e_lista_e_rejeitada() -> None:
    respx.get(URL_SIDRA_GO).respond(json={"erro": "tabela inexistente"})

    with ClienteIbge(CONFIG) as ibge, pytest.raises(ErroExtracao, match="esperava uma lista"):
        ibge.efetivo_rebanhos("GO", ultimos_anos=2)


def test_uf_invalida_falha_antes_de_acessar_a_rede() -> None:
    with pytest.raises(ValueError, match="UF desconhecida"):
        main(["--uf", "XX"])
