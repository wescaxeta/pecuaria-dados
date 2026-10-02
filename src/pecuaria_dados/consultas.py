"""Consultas analíticas em SQL. As agregações e comparações ficam no PostgreSQL (window functions),
que faz esse trabalho melhor e mais rápido do que trazer as linhas para o Python."""

from typing import Any

from sqlalchemy import Connection, text

from pecuaria_dados.dominio import Especie


def anos_disponiveis(conexao: Connection) -> list[int]:
    return list(conexao.execute(text("SELECT DISTINCT ano FROM efetivo_rebanho ORDER BY ano")).scalars())


def ufs_disponiveis(conexao: Connection) -> list[str]:
    return list(conexao.execute(text("SELECT DISTINCT uf FROM municipio ORDER BY uf")).scalars())


def buscar_municipios(
    conexao: Connection, uf: str | None, nome: str | None, limite: int
) -> list[dict[str, Any]]:
    sql = text("""
        SELECT codigo, nome, uf
        FROM municipio
        WHERE (CAST(:uf AS text) IS NULL OR uf = :uf)
          AND (CAST(:nome AS text) IS NULL OR unaccent_lower(nome) LIKE '%' || unaccent_lower(:nome) || '%')
        ORDER BY nome
        LIMIT :limite
    """)
    return _linhas(conexao.execute(sql, {"uf": uf, "nome": nome, "limite": limite}))


def municipio(conexao: Connection, codigo: int) -> dict[str, Any] | None:
    linha = (
        conexao.execute(
            text("SELECT codigo, nome, uf FROM municipio WHERE codigo = :codigo"), {"codigo": codigo}
        )
        .mappings()
        .first()
    )
    return dict(linha) if linha else None


def rebanhos_do_municipio(conexao: Connection, codigo: int, ano: int) -> list[dict[str, Any]]:
    sql = text("""
        SELECT especie, efetivo, situacao
        FROM efetivo_rebanho
        WHERE municipio_codigo = :codigo AND ano = :ano
        ORDER BY efetivo DESC NULLS LAST, especie
    """)
    return _linhas(conexao.execute(sql, {"codigo": codigo, "ano": ano}))


def ranking(conexao: Connection, uf: str, especie: Especie, ano: int, limite: int) -> list[dict[str, Any]]:
    """Maiores rebanhos da UF, com a posição e a participação de cada município no total do estado."""
    sql = text("""
        SELECT posicao, codigo, nome, efetivo, participacao_percentual
        FROM (
            SELECT m.codigo,
                   m.nome,
                   r.efetivo,
                   RANK() OVER (ORDER BY r.efetivo DESC) AS posicao,
                   ROUND(100.0 * r.efetivo / NULLIF(SUM(r.efetivo) OVER (), 0), 2) AS participacao_percentual
            FROM efetivo_rebanho r
            JOIN municipio m ON m.codigo = r.municipio_codigo
            WHERE m.uf = :uf AND r.especie = :especie AND r.ano = :ano AND r.efetivo IS NOT NULL
        ) ranqueado
        WHERE posicao <= :limite
        ORDER BY posicao, nome
    """)
    return _linhas(conexao.execute(sql, {"uf": uf, "especie": especie.value, "ano": ano, "limite": limite}))


def evolucao(conexao: Connection, uf: str, especie: Especie) -> list[dict[str, Any]]:
    """Total da UF por ano e a variação em relação ao ano anterior (LAG)."""
    sql = text("""
        WITH total_por_ano AS (
            SELECT r.ano, SUM(r.efetivo) AS efetivo
            FROM efetivo_rebanho r
            JOIN municipio m ON m.codigo = r.municipio_codigo
            WHERE m.uf = :uf AND r.especie = :especie
            GROUP BY r.ano
        )
        SELECT ano,
               efetivo,
               efetivo - LAG(efetivo) OVER (ORDER BY ano) AS variacao_absoluta,
               ROUND(
                   100.0 * (efetivo - LAG(efetivo) OVER (ORDER BY ano))
                   / NULLIF(LAG(efetivo) OVER (ORDER BY ano), 0),
                   2
               ) AS variacao_percentual
        FROM total_por_ano
        ORDER BY ano
    """)
    return _linhas(conexao.execute(sql, {"uf": uf, "especie": especie.value}))


def resumo_uf(conexao: Connection, uf: str, ano: int) -> list[dict[str, Any]]:
    """Por espécie: total, quantos municípios criam e quanto os 10 maiores concentram do total."""
    sql = text("""
        WITH base AS (
            SELECT r.especie,
                   r.efetivo,
                   ROW_NUMBER() OVER (PARTITION BY r.especie ORDER BY r.efetivo DESC) AS posicao
            FROM efetivo_rebanho r
            JOIN municipio m ON m.codigo = r.municipio_codigo
            WHERE m.uf = :uf AND r.ano = :ano AND r.efetivo IS NOT NULL
        )
        SELECT especie,
               SUM(efetivo) AS efetivo_total,
               COUNT(*) FILTER (WHERE efetivo > 0) AS municipios_com_rebanho,
               ROUND(
                   100.0 * SUM(efetivo) FILTER (WHERE posicao <= 10) / NULLIF(SUM(efetivo), 0),
                   2
               ) AS concentracao_top10_percentual
        FROM base
        GROUP BY especie
        ORDER BY efetivo_total DESC
    """)
    return _linhas(conexao.execute(sql, {"uf": uf, "ano": ano}))


def _linhas(resultado: Any) -> list[dict[str, Any]]:
    return [dict(linha) for linha in resultado.mappings()]
