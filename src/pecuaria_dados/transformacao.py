"""Transformação dos dados brutos do SIDRA em tabelas limpas e tipadas (pandas)."""

import logging
from typing import Any

import pandas as pd

from pecuaria_dados.dominio import CODIGOS_SIDRA, Situacao

logger = logging.getLogger(__name__)

COLUNAS_EFETIVO = ["municipio_codigo", "ano", "especie", "efetivo", "situacao"]


class ErroDadosInconsistentes(ValueError):
    """Os dados extraídos violam alguma premissa (chave duplicada, valor negativo...)."""


def _interpretar_valor(valor: str) -> tuple[int | None, Situacao]:
    texto = valor.strip()
    if texto == "-":
        return 0, Situacao.INFORMADO
    if texto.upper() == "X":
        return None, Situacao.SIGILOSO
    if texto.isdigit():
        return int(texto), Situacao.INFORMADO
    return None, Situacao.NAO_DISPONIVEL  # "...", ".." e qualquer outro marcador


def efetivo_rebanhos(registros: list[dict[str, Any]]) -> pd.DataFrame:
    """Converte as linhas do SIDRA (V, D1C, D3C, D4C) em uma linha por município, ano e espécie."""
    if not registros:
        return pd.DataFrame(columns=COLUNAS_EFETIVO)

    bruto = pd.DataFrame(registros)
    desconhecidas = set(bruto["D4C"]) - set(CODIGOS_SIDRA)
    if desconhecidas:
        logger.warning("Ignorando categorias de rebanho desconhecidas: %s", sorted(desconhecidas))
        bruto = bruto[bruto["D4C"].isin(list(CODIGOS_SIDRA))]

    interpretados = [_interpretar_valor(str(v)) for v in bruto["V"]]

    df = pd.DataFrame(
        {
            "municipio_codigo": bruto["D1C"].astype(int).to_numpy(),
            "ano": bruto["D3C"].astype(int).to_numpy(),
            "especie": bruto["D4C"].map(lambda codigo: CODIGOS_SIDRA[codigo].value).to_numpy(),
            "efetivo": pd.array([valor for valor, _ in interpretados], dtype="Int64"),
            "situacao": [situacao.value for _, situacao in interpretados],
        }
    )

    _validar(df)
    return df.sort_values(["municipio_codigo", "ano", "especie"]).reset_index(drop=True)


def municipios(registros: list[dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(registros, columns=["codigo", "nome", "uf"])
    if df["codigo"].duplicated().any():
        raise ErroDadosInconsistentes("Município duplicado na resposta do IBGE.")
    return df


def _validar(df: pd.DataFrame) -> None:
    chave = ["municipio_codigo", "ano", "especie"]
    duplicadas = df.duplicated(subset=chave)
    if duplicadas.any():
        exemplo = df.loc[duplicadas, chave].iloc[0].to_dict()
        raise ErroDadosInconsistentes(f"Registro duplicado para {exemplo}.")

    if (df["efetivo"].dropna() < 0).any():
        raise ErroDadosInconsistentes("Efetivo negativo encontrado.")
