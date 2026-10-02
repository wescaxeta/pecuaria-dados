"""Vocabulário do domínio: espécies, situações do dado e unidades da federação."""

from enum import StrEnum


class Especie(StrEnum):
    """Tipos de rebanho da Pesquisa da Pecuária Municipal (tabela 3939 do SIDRA)."""

    BOVINO = "bovino"
    BUBALINO = "bubalino"
    EQUINO = "equino"
    SUINO = "suino"
    SUINO_MATRIZES = "suino_matrizes"
    CAPRINO = "caprino"
    OVINO = "ovino"
    GALINACEOS = "galinaceos"
    GALINHAS = "galinhas"
    CODORNAS = "codornas"


# Código da categoria "Tipo de rebanho" (classificação 79) no SIDRA
CODIGOS_SIDRA: dict[str, Especie] = {
    "2670": Especie.BOVINO,
    "2675": Especie.BUBALINO,
    "2672": Especie.EQUINO,
    "32794": Especie.SUINO,
    "32795": Especie.SUINO_MATRIZES,
    "2681": Especie.CAPRINO,
    "2677": Especie.OVINO,
    "32796": Especie.GALINACEOS,
    "32793": Especie.GALINHAS,
    "2680": Especie.CODORNAS,
}


class Situacao(StrEnum):
    """Como o IBGE publicou o valor. Só ``informado`` tem número; os demais ficam nulos.

    Convenção do SIDRA: "-" é zero absoluto (informado = 0), "..." ou ".." é dado não
    disponível e "X" é dado omitido para não identificar o informante.
    """

    INFORMADO = "informado"
    NAO_DISPONIVEL = "nao_disponivel"
    SIGILOSO = "sigiloso"


# Código IBGE de cada UF (usado pela API SIDRA no nível territorial n3)
UFS: dict[str, int] = {
    "RO": 11, "AC": 12, "AM": 13, "RR": 14, "PA": 15, "AP": 16, "TO": 17,
    "MA": 21, "PI": 22, "CE": 23, "RN": 24, "PB": 25, "PE": 26, "AL": 27, "SE": 28, "BA": 29,
    "MG": 31, "ES": 32, "RJ": 33, "SP": 35,
    "PR": 41, "SC": 42, "RS": 43,
    "MS": 50, "MT": 51, "GO": 52, "DF": 53,
}  # fmt: skip


def codigo_uf(sigla: str) -> int:
    try:
        return UFS[sigla.strip().upper()]
    except KeyError:
        raise ValueError(f"UF desconhecida: {sigla!r}") from None
