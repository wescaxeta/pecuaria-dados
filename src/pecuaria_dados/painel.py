"""Painel (Streamlit) que consome a API. Rode com: streamlit run src/pecuaria_dados/painel.py"""

import os
from typing import Any

import altair as alt
import httpx
import pandas as pd
import streamlit as st

API_URL = os.environ.get("API_URL", "http://localhost:8000")

NOMES_ESPECIES = {
    "bovino": "Bovinos", "bubalino": "Bubalinos", "equino": "Equinos", "suino": "Suínos",
    "suino_matrizes": "Suínos (matrizes)", "caprino": "Caprinos", "ovino": "Ovinos",
    "galinaceos": "Galináceos", "galinhas": "Galinhas", "codornas": "Codornas",
}  # fmt: skip

# Rótulo de eixo abreviado no padrão brasileiro: 24,6 mi · 800 mil · 350
ROTULO_ABREVIADO = (
    "datum.value >= 1e6 ? replace(format(datum.value / 1e6, '.1f'), '.', ',') + ' mi'"
    " : datum.value >= 1e3 ? format(datum.value / 1e3, '.0f') + ' mil'"
    " : format(datum.value, '.0f')"
)


@st.cache_data(ttl=300)
def consultar(caminho: str, **parametros: Any) -> Any:
    resposta = httpx.get(f"{API_URL}{caminho}", params=parametros, timeout=30)
    resposta.raise_for_status()
    return resposta.json()


def numero(valor: float) -> str:
    return f"{valor:,.0f}".replace(",", ".")


def percentual(valor: float, sinal: bool = False) -> str:
    return (f"{valor:+.2f}" if sinal else f"{valor:.1f}").replace(".", ",") + "%"


st.set_page_config(page_title="Pecuária em Dados", page_icon="🐄", layout="wide")
st.title("🐄 Pecuária em Dados")
st.caption("Efetivo dos rebanhos por município · Fonte: IBGE, Pesquisa da Pecuária Municipal (tabela 3939)")

metadados = consultar("/metadados")
if not metadados["anos"]:
    st.warning("Nenhum dado carregado ainda. Rode o ETL: `pecuaria-etl --uf GO`.")
    st.stop()

coluna_uf, coluna_especie, coluna_ano = st.columns(3)
uf = coluna_uf.selectbox("UF", metadados["ufs"])
especie = coluna_especie.selectbox(
    "Rebanho", metadados["especies"], format_func=lambda e: NOMES_ESPECIES.get(e, e)
)
ano = coluna_ano.selectbox("Ano", list(reversed(metadados["anos"])))

evolucao = pd.DataFrame(consultar(f"/ufs/{uf}/evolucao", especie=especie))
ranking = pd.DataFrame(consultar(f"/ufs/{uf}/ranking", especie=especie, ano=ano, limite=15))
resumo = pd.DataFrame(consultar(f"/ufs/{uf}/resumo", ano=ano))

linha_ano = evolucao[evolucao["ano"] == ano]
if not linha_ano.empty:
    atual = linha_ano.iloc[0]
    metrica_total, metrica_variacao, metrica_concentracao = st.columns(3)
    metrica_total.metric(
        f"{NOMES_ESPECIES.get(especie, especie)} em {uf} ({ano})", numero(atual["efetivo"] or 0)
    )
    variacao = atual["variacao_percentual"]
    metrica_variacao.metric(
        "Variação sobre o ano anterior",
        percentual(float(variacao), sinal=True) if pd.notna(variacao) else "—",
    )
    concentracao = resumo.loc[resumo["especie"] == especie, "concentracao_top10_percentual"]
    if not concentracao.empty and pd.notna(concentracao.iloc[0]):
        metrica_concentracao.metric(
            "Concentração nos 10 maiores municípios", percentual(float(concentracao.iloc[0]))
        )

coluna_evolucao, coluna_ranking = st.columns(2, gap="large")

with coluna_evolucao:
    st.subheader("Evolução no estado")
    # Eixo Y sem começar no zero, para a tendência ficar visível
    grafico_evolucao = (
        alt.Chart(evolucao)
        .mark_line(point=True, strokeWidth=3)
        .encode(
            x=alt.X("ano:O", title="Ano", axis=alt.Axis(labelAngle=0)),
            y=alt.Y(
                "efetivo:Q",
                title="Cabeças",
                scale=alt.Scale(zero=False),
                axis=alt.Axis(labelExpr=ROTULO_ABREVIADO),
            ),
            tooltip=[
                alt.Tooltip("ano:O", title="Ano"),
                alt.Tooltip("efetivo:Q", title="Cabeças", format=",.0f"),
                alt.Tooltip("variacao_percentual:Q", title="Variação (%)", format="+.2f"),
            ],
        )
        .properties(height=420)
    )
    st.altair_chart(grafico_evolucao, use_container_width=True)

with coluna_ranking:
    st.subheader(f"Maiores municípios em {ano}")
    if ranking.empty:
        st.info("Sem dados para esta combinação.")
    else:
        grafico_ranking = (
            alt.Chart(ranking)
            .mark_bar()
            .encode(
                x=alt.X("efetivo:Q", title="Cabeças", axis=alt.Axis(labelExpr=ROTULO_ABREVIADO)),
                y=alt.Y("nome:N", title=None, sort="-x"),
                tooltip=[
                    alt.Tooltip("nome:N", title="Município"),
                    alt.Tooltip("efetivo:Q", title="Cabeças", format=",.0f"),
                    alt.Tooltip("participacao_percentual:Q", title="% do estado", format=".2f"),
                ],
            )
            .properties(height=420)
        )
        st.altair_chart(grafico_ranking, use_container_width=True)

if not ranking.empty:
    with st.expander("Tabela do ranking"):
        st.dataframe(
            ranking.rename(
                columns={
                    "posicao": "#",
                    "nome": "Município",
                    "efetivo": "Cabeças",
                    "participacao_percentual": "% do estado",
                }
            ),
            hide_index=True,
            column_order=["#", "Município", "Cabeças", "% do estado"],
        )
