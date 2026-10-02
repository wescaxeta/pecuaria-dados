"""Carga idempotente no PostgreSQL: rodar o ETL de novo atualiza os dados, sem duplicar."""

from dataclasses import dataclass
from typing import Any

import pandas as pd
from sqlalchemy import Connection, Table
from sqlalchemy.dialects.postgresql import insert

from pecuaria_dados.db import efetivo_rebanho, municipio

TAMANHO_LOTE = 2_000


@dataclass(frozen=True)
class ResultadoCarga:
    municipios: int
    registros_efetivo: int


def carregar(conexao: Connection, municipios: pd.DataFrame, efetivos: pd.DataFrame) -> ResultadoCarga:
    """Grava municípios e efetivos em uma única transação (tudo ou nada)."""
    with conexao.begin():
        _upsert(conexao, municipio, _linhas(municipios), chave=["codigo"])
        _upsert(conexao, efetivo_rebanho, _linhas(efetivos), chave=["municipio_codigo", "ano", "especie"])

    return ResultadoCarga(municipios=len(municipios), registros_efetivo=len(efetivos))


def _linhas(df: pd.DataFrame) -> list[dict[str, Any]]:
    # Converte pd.NA / NaN em None, que o driver grava como NULL
    return [
        {str(coluna): (None if pd.isna(valor) else valor) for coluna, valor in linha.items()}
        for linha in df.astype(object).to_dict(orient="records")
    ]


def _upsert(conexao: Connection, tabela: Table, linhas: list[dict[str, Any]], chave: list[str]) -> None:
    for inicio in range(0, len(linhas), TAMANHO_LOTE):
        lote = linhas[inicio : inicio + TAMANHO_LOTE]
        comando = insert(tabela).values(lote)
        atualizar = {c.name: comando.excluded[c.name] for c in tabela.columns if c.name not in chave}
        conexao.execute(comando.on_conflict_do_update(index_elements=chave, set_=atualizar))
