import pandas as pd
import pytest

from pecuaria_dados import transformacao
from pecuaria_dados.transformacao import ErroDadosInconsistentes
from tests.dados import BOVINO, EFETIVO_GO, MUNICIPIOS_GO, linha_sidra


def _linha(df: pd.DataFrame, municipio: int, ano: int, especie: str) -> pd.Series:
    filtro = (df["municipio_codigo"] == municipio) & (df["ano"] == ano) & (df["especie"] == especie)
    return df.loc[filtro].iloc[0]


def test_converte_para_uma_linha_tipada_por_municipio_ano_e_especie() -> None:
    df = transformacao.efetivo_rebanhos(EFETIVO_GO)

    assert list(df.columns) == transformacao.COLUNAS_EFETIVO
    assert len(df) == len(EFETIVO_GO)
    assert str(df["efetivo"].dtype) == "Int64"
    assert _linha(df, 5200002, 2025, "bovino")["efetivo"] == 600


@pytest.mark.parametrize(
    ("municipio", "especie", "efetivo", "situacao"),
    [
        pytest.param(5200001, "suino", 0, "informado", id="traço é zero absoluto"),
        pytest.param(5200003, "suino", None, "nao_disponivel", id="reticências é não disponível"),
        pytest.param(5200002, "caprino", None, "sigiloso", id="X é sigiloso"),
    ],
)
def test_interpreta_os_marcadores_do_ibge(
    municipio: int, especie: str, efetivo: int | None, situacao: str
) -> None:
    linha = _linha(transformacao.efetivo_rebanhos(EFETIVO_GO), municipio, 2025, especie)

    assert pd.isna(linha["efetivo"]) if efetivo is None else linha["efetivo"] == efetivo
    assert linha["situacao"] == situacao


def test_ignora_categoria_desconhecida_sem_quebrar(caplog: pytest.LogCaptureFixture) -> None:
    df = transformacao.efetivo_rebanhos([*EFETIVO_GO, linha_sidra(5200001, 2025, "99999", "10")])

    assert len(df) == len(EFETIVO_GO)
    assert "99999" in caplog.text


def test_rejeita_registro_duplicado() -> None:
    with pytest.raises(ErroDadosInconsistentes, match="duplicado"):
        transformacao.efetivo_rebanhos([*EFETIVO_GO, linha_sidra(5200001, 2024, BOVINO, "1")])


def test_lista_vazia_gera_tabela_vazia_com_as_colunas_certas() -> None:
    df = transformacao.efetivo_rebanhos([])

    assert df.empty
    assert list(df.columns) == transformacao.COLUNAS_EFETIVO


def test_rejeita_municipio_duplicado() -> None:
    with pytest.raises(ErroDadosInconsistentes):
        transformacao.municipios([*MUNICIPIOS_GO, MUNICIPIOS_GO[0]])
