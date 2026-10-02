"""Linha de comando do pipeline: extrai do IBGE, transforma e carrega no PostgreSQL.

Exemplo:
    pecuaria-etl --uf GO --uf MT --uf MS --anos 5
"""

import argparse
import logging
import time

from pecuaria_dados import transformacao
from pecuaria_dados.carga import carregar
from pecuaria_dados.config import configuracao
from pecuaria_dados.db import engine
from pecuaria_dados.dominio import codigo_uf
from pecuaria_dados.extracao import ClienteIbge

logger = logging.getLogger("pecuaria_dados.etl")


def executar(ufs: list[str], anos: int) -> None:
    config = configuracao()

    with ClienteIbge(config) as ibge, engine().connect() as conexao:
        for uf in ufs:
            inicio = time.perf_counter()

            municipios = transformacao.municipios(ibge.municipios(uf))
            efetivos = transformacao.efetivo_rebanhos(ibge.efetivo_rebanhos(uf, anos))
            resultado = carregar(conexao, municipios, efetivos)

            logger.info(
                "UF %s carregada: %d municípios, %d registros de efetivo em %.1fs",
                uf, resultado.municipios, resultado.registros_efetivo, time.perf_counter() - inicio,
            )  # fmt: skip


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Carrega o efetivo dos rebanhos (IBGE/PPM) no PostgreSQL.")
    parser.add_argument("--uf", action="append", required=True, help="Sigla da UF (repita para várias)")
    parser.add_argument("--anos", type=int, default=5, help="Quantidade de anos mais recentes (padrão: 5)")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    ufs = [uf.upper() for uf in args.uf]
    for uf in ufs:
        codigo_uf(uf)  # falha cedo para siglas inválidas, antes de qualquer chamada de rede
    if not 1 <= args.anos <= 50:  # noqa: PLR2004
        parser.error("--anos deve ficar entre 1 e 50")

    executar(ufs, args.anos)


if __name__ == "__main__":
    main()
