# pecuaria-dados

[![CI](https://github.com/wescaxeta/pecuaria-dados/actions/workflows/ci.yml/badge.svg)](https://github.com/wescaxeta/pecuaria-dados/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![pandas](https://img.shields.io/badge/pandas-150458?logo=pandas&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-4169E1?logo=postgresql&logoColor=white)
![mypy](https://img.shields.io/badge/mypy-strict-2A6DB2)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Pipeline de **dados públicos reais do IBGE** sobre o rebanho brasileiro: extrai a Pesquisa da Pecuária
Municipal (PPM), trata com pandas, grava no PostgreSQL e expõe os dados numa **API (FastAPI)** e num
**painel (Streamlit)**.

![Painel com o rebanho bovino de Goiás](docs/painel.png)

## O que os dados mostram

Com os dados de 2021 a 2025 de GO, MT e MS (cerca de 23 mil registros de 467 municípios):

- **O rebanho bovino do Centro-Oeste está encolhendo.** Mato Grosso caiu três anos seguidos, de 34,2 milhões
  de cabeças (2022) para 31,6 milhões (2025), e Goiás teve queda de 3,25% em 2025.
- **A pecuária bovina é pulverizada; a avicultura, concentrada.** Em Goiás, os 10 maiores municípios
  têm 19% dos bovinos, mas 57% dos galináceos.
- **Nova Crixás (GO) e Cáceres (MT)** lideram o rebanho bovino em seus estados.

> Todos os números vêm do IBGE (SIDRA, tabela 3939) e são recalculados a cada execução do ETL.

## Arquitetura

```mermaid
flowchart LR
    SIDRA["API SIDRA (IBGE)<br/>efetivo dos rebanhos"] --> E
    LOC["API Localidades (IBGE)<br/>municípios"] --> E
    subgraph ETL["ETL (pecuaria-etl)"]
        E[Extração<br/>httpx + retry] --> T[Transformação<br/>pandas] --> C[Carga<br/>upsert idempotente]
    end
    C --> DB[(PostgreSQL)]
    DB --> API["API<br/>FastAPI"]
    API --> P["Painel<br/>Streamlit"]
```

| Etapa | Arquivo | Destaques |
|---|---|---|
| **Extração** | [`extracao.py`](src/pecuaria_dados/extracao.py) | `httpx` com timeout e **retry com backoff exponencial** (`tenacity`) só em falhas transitórias (rede e 5xx) |
| **Transformação** | [`transformacao.py`](src/pecuaria_dados/transformacao.py) | Interpreta as convenções do IBGE: `-` é zero, `...` é dado não disponível e `X` é sigiloso. Valida chaves duplicadas e valores negativos |
| **Carga** | [`carga.py`](src/pecuaria_dados/carga.py) | **Upsert** (`INSERT ... ON CONFLICT DO UPDATE`) em lotes e numa única transação: rodar de novo atualiza sem duplicar |
| **Banco** | [`migrations/`](migrations/versions/0001_esquema_inicial.py) | **Alembic**, `CHECK` constraints coerentes com o domínio e índice de busca sem acento (`unaccent`) |
| **Análises** | [`consultas.py`](src/pecuaria_dados/consultas.py) | SQL com **window functions**: `RANK()` e participação com `SUM() OVER ()`, variação anual com `LAG()`, concentração com `ROW_NUMBER()` e `FILTER` |
| **API** | [`api.py`](src/pecuaria_dados/api.py) | FastAPI com modelos Pydantic, validação de parâmetros e documentação automática em `/docs` |
| **Painel** | [`painel.py`](src/pecuaria_dados/painel.py) | Streamlit + Altair consumindo a API, com números no padrão brasileiro |

## Como rodar

Requisito: Docker.

```bash
git clone https://github.com/wescaxeta/pecuaria-dados.git
cd pecuaria-dados
docker compose up --build
```

O ETL roda primeiro (baixa os dados reais do IBGE em poucos segundos) e depois sobem:

- **Painel:** http://localhost:8501
- **API (documentação interativa):** http://localhost:8000/docs

### Sem Docker

```bash
uv sync --all-extras                       # instala tudo (gerenciado pelo uv)
export DATABASE_URL=postgresql+psycopg://usuario:senha@localhost:5432/pecuaria
uv run alembic upgrade head
uv run pecuaria-etl --uf GO --uf MT --uf MS --anos 5
uv run uvicorn pecuaria_dados.api:app --reload
uv run streamlit run src/pecuaria_dados/painel.py
```

## Endpoints

| Rota | Descrição |
|---|---|
| `GET /metadados` | UFs, anos e espécies disponíveis |
| `GET /municipios?uf=&nome=` | Busca de municípios (ignora acentos: `goiania` encontra Goiânia) |
| `GET /municipios/{codigo}/rebanhos?ano=` | Todos os rebanhos de um município |
| `GET /ufs/{uf}/ranking?especie=&ano=&limite=` | Maiores municípios, com posição e % do estado |
| `GET /ufs/{uf}/evolucao?especie=` | Total por ano e variação sobre o ano anterior |
| `GET /ufs/{uf}/resumo?ano=` | Por espécie: total, municípios com rebanho e concentração nos 10 maiores |

Sem `ano`, a API usa o ano mais recente carregado.

## Qualidade

- **pytest**: 27 testes, com 93% de cobertura.
  - Transformação: cada marcador do IBGE e cada regra de validação.
  - Extração: com `respx` (sem rede), cobrindo retry em 5xx e queda de conexão, sem retry em 4xx.
  - Carga e API contra **PostgreSQL real**, com o esquema criado pelas próprias migrations.
- **mypy `--strict`** e **ruff** (lint + formatação), com warnings tratados como erro nos testes.
- **CI** no GitHub Actions em três jobs. O de ponta a ponta sobe tudo com Docker Compose, roda o ETL com
  os **dados reais do IBGE** e executa o smoke test na API e no painel.
- Dependências travadas no `uv.lock` e build reprodutível.

## Contexto

Este projeto completa um pequeno ecossistema de defesa agropecuária em três linguagens, baseado na
minha experiência com sistemas usados em 9 estados:

- [gta-integration-service](https://github.com/wescaxeta/gta-integration-service) (PHP): emissão de GTA, com integração SOAP e REST
- [vacinacao-api](https://github.com/wescaxeta/vacinacao-api) (.NET): vacinação e aptidão do rebanho para transporte
- **pecuaria-dados** (Python): dados públicos reais do rebanho por município

## Fonte dos dados

IBGE, Pesquisa da Pecuária Municipal, [tabela 3939](https://sidra.ibge.gov.br/tabela/3939): efetivo dos
rebanhos por tipo de rebanho. Dados públicos, acessados pela API SIDRA.

## Licença

[MIT](LICENSE)
