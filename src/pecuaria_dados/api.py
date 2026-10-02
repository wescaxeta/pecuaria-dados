"""API de consulta ao efetivo dos rebanhos (FastAPI). Documentação interativa em /docs."""

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import Connection, text

from pecuaria_dados import consultas
from pecuaria_dados.db import engine
from pecuaria_dados.dominio import UFS, Especie

app = FastAPI(
    title="Pecuária em Dados",
    description="Efetivo dos rebanhos por município, a partir da Pesquisa da Pecuária Municipal (IBGE).",
    version="0.1.0",
)


def obter_conexao() -> Iterator[Connection]:
    with engine().connect() as conexao:
        yield conexao


Conexao = Annotated[Connection, Depends(obter_conexao)]
Uf = Annotated[str, Query(pattern="^[A-Za-z]{2}$", description="Sigla da UF, ex.: GO")]


class Municipio(BaseModel):
    codigo: int
    nome: str
    uf: str


class Rebanho(BaseModel):
    especie: Especie
    efetivo: int | None
    situacao: str


class RebanhosDoMunicipio(BaseModel):
    municipio: Municipio
    ano: int
    rebanhos: list[Rebanho]


class PosicaoRanking(BaseModel):
    posicao: int
    codigo: int
    nome: str
    efetivo: int
    participacao_percentual: float | None


class AnoEvolucao(BaseModel):
    ano: int
    efetivo: int | None
    variacao_absoluta: int | None
    variacao_percentual: float | None


class ResumoEspecie(BaseModel):
    especie: Especie
    efetivo_total: int
    municipios_com_rebanho: int
    concentracao_top10_percentual: float | None


class Metadados(BaseModel):
    ufs: list[str]
    anos: list[int]
    especies: list[Especie]


def _uf_valida(uf: str) -> str:
    sigla = uf.upper()
    if sigla not in UFS:
        raise HTTPException(status_code=422, detail=f"UF desconhecida: {uf}")
    return sigla


def _ano_ou_mais_recente(conexao: Connection, ano: int | None) -> int:
    anos = consultas.anos_disponiveis(conexao)
    if not anos:
        raise HTTPException(status_code=404, detail="Nenhum dado carregado. Rode o ETL primeiro.")
    if ano is None:
        return anos[-1]
    if ano not in anos:
        raise HTTPException(status_code=404, detail=f"Ano {ano} não carregado. Disponíveis: {anos}")
    return ano


@app.get("/health", tags=["infra"])
def health(conexao: Conexao) -> dict[str, str]:
    conexao.execute(text("SELECT 1"))
    return {"status": "ok"}


@app.get("/metadados", tags=["consultas"])
def metadados(conexao: Conexao) -> Metadados:
    """UFs e anos carregados, e as espécies disponíveis."""
    return Metadados(
        ufs=consultas.ufs_disponiveis(conexao),
        anos=consultas.anos_disponiveis(conexao),
        especies=list(Especie),
    )


@app.get("/municipios", tags=["consultas"])
def buscar_municipios(
    conexao: Conexao,
    uf: Annotated[str | None, Query(pattern="^[A-Za-z]{2}$")] = None,
    nome: Annotated[str | None, Query(min_length=2, max_length=100, description="Busca sem acento")] = None,
    limite: Annotated[int, Query(ge=1, le=500)] = 50,
) -> list[Municipio]:
    linhas = consultas.buscar_municipios(conexao, _uf_valida(uf) if uf else None, nome, limite)
    return [Municipio.model_validate(linha) for linha in linhas]


@app.get("/municipios/{codigo}/rebanhos", tags=["consultas"])
def rebanhos_do_municipio(conexao: Conexao, codigo: int, ano: int | None = None) -> RebanhosDoMunicipio:
    dados = consultas.municipio(conexao, codigo)
    if dados is None:
        raise HTTPException(status_code=404, detail=f"Município {codigo} não encontrado.")

    ano_consulta = _ano_ou_mais_recente(conexao, ano)
    return RebanhosDoMunicipio(
        municipio=Municipio.model_validate(dados),
        ano=ano_consulta,
        rebanhos=[
            Rebanho.model_validate(r) for r in consultas.rebanhos_do_municipio(conexao, codigo, ano_consulta)
        ],
    )


@app.get("/ufs/{uf}/ranking", tags=["análises"])
def ranking(
    conexao: Conexao,
    uf: str,
    especie: Especie = Especie.BOVINO,
    ano: int | None = None,
    limite: Annotated[int, Query(ge=1, le=100)] = 10,
) -> list[PosicaoRanking]:
    """Maiores rebanhos da UF, com a participação de cada município no total do estado."""
    linhas = consultas.ranking(conexao, _uf_valida(uf), especie, _ano_ou_mais_recente(conexao, ano), limite)
    return [PosicaoRanking.model_validate(linha) for linha in linhas]


@app.get("/ufs/{uf}/evolucao", tags=["análises"])
def evolucao(conexao: Conexao, uf: str, especie: Especie = Especie.BOVINO) -> list[AnoEvolucao]:
    """Total da UF por ano, com a variação em relação ao ano anterior."""
    return [
        AnoEvolucao.model_validate(linha) for linha in consultas.evolucao(conexao, _uf_valida(uf), especie)
    ]


@app.get("/ufs/{uf}/resumo", tags=["análises"])
def resumo(conexao: Conexao, uf: str, ano: int | None = None) -> list[ResumoEspecie]:
    """Por espécie: total, municípios que criam e concentração nos 10 maiores municípios."""
    linhas = consultas.resumo_uf(conexao, _uf_valida(uf), _ano_ou_mais_recente(conexao, ano))
    return [ResumoEspecie.model_validate(linha) for linha in linhas]
