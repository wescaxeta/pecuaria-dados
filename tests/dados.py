"""Dados de exemplo no mesmo formato das APIs do IBGE, com números redondos para facilitar as contas."""

from typing import Any

BOVINO, SUINO, CAPRINO = "2670", "32794", "2681"


def linha_sidra(municipio: int, ano: int, categoria: str, valor: str) -> dict[str, Any]:
    return {
        "NC": "6",
        "MC": "24",
        "V": valor,
        "D1C": str(municipio),
        "D2C": "105",
        "D3C": str(ano),
        "D4C": categoria,
    }


CABECALHO_SIDRA: dict[str, Any] = {
    "NC": "Nível Territorial (Código)",
    "MC": "Unidade de Medida (Código)",
    "V": "Valor",
    "D1C": "Município (Código)",
    "D2C": "Variável (Código)",
    "D3C": "Ano (Código)",
    "D4C": "Tipo de rebanho (Código)",
}

# Três municípios fictícios de GO. Bovinos: 2024 → 1.000 cabeças; 2025 → 1.200 (+20%).
MUNICIPIOS_GO: list[dict[str, Any]] = [
    {"codigo": 5200001, "nome": "Goiânia", "uf": "GO"},
    {"codigo": 5200002, "nome": "Rio Verde", "uf": "GO"},
    {"codigo": 5200003, "nome": "Jataí", "uf": "GO"},
]

EFETIVO_GO: list[dict[str, Any]] = [
    linha_sidra(5200001, 2024, BOVINO, "100"),
    linha_sidra(5200002, 2024, BOVINO, "600"),
    linha_sidra(5200003, 2024, BOVINO, "300"),
    linha_sidra(5200001, 2025, BOVINO, "200"),
    linha_sidra(5200002, 2025, BOVINO, "600"),
    linha_sidra(5200003, 2025, BOVINO, "400"),
    linha_sidra(5200001, 2025, SUINO, "-"),  # zero absoluto
    linha_sidra(5200002, 2025, SUINO, "50"),
    linha_sidra(5200003, 2025, SUINO, "..."),  # não disponível
    linha_sidra(5200002, 2025, CAPRINO, "X"),  # sigiloso
]
