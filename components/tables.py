import urllib.request
import json
import pandas as pd
import plotly.express as px
import streamlit as st


@st.cache_data(ttl=86400, show_spinner=False)
def _load_brazil_states_geojson():
    """Carrega o GeoJSON oficial dos estados brasileiros (sigla UF) com cache."""
    url = "https://raw.githubusercontent.com/codeforamerica/click_that_hood/master/public/data/brazil-states.geojson"
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception:
        return None


def _format_brl(val: float) -> str:
    return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def render_top10_faturamento(df_fat_detalhado: pd.DataFrame, unidade_selecionada: str = "Todas as Unidades (Geral)"):
    st.markdown("---")
    st.markdown("### 🏆 Top 10 Clientes por Faturamento Monetário & Distribuição Geográfica (UF)")

    if df_fat_detalhado is None or df_fat_detalhado.empty:
        st.info("Sem dados detalhados por cliente na aba 'Faturamento por cliente'.")
        return

    df = df_fat_detalhado.copy()
    df.columns = [str(c).strip() for c in df.columns]

    # Normaliza nomes das colunas esperadas: ['Mês', 'Filial', 'Loja', 'UF', 'Cliente', 'R$ Fatur.']
    col_valor = next((c for c in df.columns if "FATUR" in c.upper() or "VALOR" in c.upper()), df.columns[-1])
    df[col_valor] = pd.to_numeric(df[col_valor], errors="coerce").fillna(0.0)

    if "Loja" in df.columns:
        df["Loja"] = df["Loja"].fillna("-").apply(
            lambda x: str(int(float(x))) if str(x).replace(".", "", 1).isdigit() else str(x).strip()
        )
    else:
        df["Loja"] = "-"

    if "UF" in df.columns:
        df["UF"] = df["UF"].fillna("N/I").astype(str).str.strip().str.upper()
    else:
        df["UF"] = "N/I"

    if "Cliente" in df.columns:
        df["Cliente"] = df["Cliente"].fillna("NÃO INFORMADO").astype(str).str.strip().str.upper()

    # Filtro opcional por Mês na aba de clientes
    if "Mês" in df.columns:
        df["Mes_Dt"] = pd.to_datetime(df["Mês"], errors="coerce")
        meses_disp = sorted(df["Mes_Dt"].dropna().dt.strftime("%Y-%m").unique().tolist())
        if meses_disp:
            opcoes_mes = ["Todos os Meses (Acumulado)"] + meses_disp
            mes_cli_sel = st.selectbox(
                "📅 Filtrar Competência (Clientes & UFs):",
                opcoes_mes,
                index=0,
                key="filtro_mes_top10_clientes",
            )
            if mes_cli_sel != "Todos os Meses (Acumulado)":
                df = df[df["Mes_Dt"].dt.strftime("%Y-%m") == mes_cli_sel].copy()

    # Filtro por Filial caso não seja Geral
    if "Filial" in df.columns and unidade_selecionada != "Todas as Unidades (Geral)":
        cod_filial = unidade_selecionada.split("-")[0].strip().lstrip("0")
        df["Filial_Str"] = df["Filial"].astype(str).str.strip().str.lstrip("0")
        if cod_filial in df["Filial_Str"].unique():
            df = df[df["Filial_Str"] == cod_filial].copy()

    if df.empty:
        st.warning("Nenhum faturamento encontrado para o filtro selecionado.")
        return

    total_faturado_geral = df[col_valor].sum()

    # =========================================================================
    # 1. TOP 10 CLIENTES DIFERENCIADOS POR CLIENTE + LOJA + UF
    # =========================================================================
    df_top10 = (
        df.groupby(["Cliente", "Loja", "UF"], as_index=False)[col_valor]
        .sum()
        .sort_values(col_valor, ascending=False)
        .head(10)
        .reset_index(drop=True)
    )
    df_top10.index = df_top10.index + 1
    df_top10.index.name = "Rank"

    df_top10["Participacao"] = (df_top10[col_valor] / total_faturado_geral * 100) if total_faturado_geral > 0 else 0.0
    df_top10["Valor_Faturado_Str"] = df_top10[col_valor].apply(_format_brl)
    df_top10["Participacao_Str"] = df_top10["Participacao"].apply(lambda p: f"{p:.2f}%")

    st.markdown("#### 🥇 Ranking Top 10 Clientes (Diferenciado por Loja & UF)")
    st.dataframe(
        df_top10[["Cliente", "Loja", "UF", "Valor_Faturado_Str", "Participacao_Str"]].rename(
            columns={
                "Cliente": "Cliente",
                "Loja": "Loja",
                "UF": "UF",
                "Valor_Faturado_Str": "Valor Faturado (R$)",
                "Participacao_Str": "% Representatividade",
            }
        ),
        use_container_width=True,
    )

    # =========================================================================
    # 2. MAPA DO BRASIL POR UF + RANKING DE FATURAMENTO POR UF
    # =========================================================================
    st.markdown("---")
    st.markdown("#### 🗺️ Mapa de Faturamento por Estado (UF) & Ranking Regional")

    df_uf = (
        df[df["UF"].str.len() == 2]
        .groupby("UF", as_index=False)
        .agg(
            Valor_Faturado=(col_valor, "sum"),
            Qtd_Clientes=("Cliente", "nunique"),
            Qtd_Lojas=("Loja", "count"),
        )
        .sort_values("Valor_Faturado", ascending=False)
        .reset_index(drop=True)
    )

    df_uf["Participacao"] = (df_uf["Valor_Faturado"] / total_faturado_geral * 100) if total_faturado_geral > 0 else 0.0
    df_uf["Valor_Faturado_Fmt"] = df_uf["Valor_Faturado"].apply(_format_brl)

    col_mapa, col_rank_uf = st.columns([1.35, 1.0])

    with col_mapa:
        geojson_br = _load_brazil_states_geojson()
        if geojson_br is not None and not df_uf.empty:
            fig_mapa = px.choropleth(
                df_uf,
                geojson=geojson_br,
                locations="UF",
                featureidkey="properties.sigla",
                color="Valor_Faturado",
                color_continuous_scale="Blues",
                hover_name="UF",
                hover_data={
                    "UF": False,
                    "Valor_Faturado": False,
                    "Valor_Faturado_Fmt": True,
                    "Qtd_Clientes": True,
                    "Participacao": ":.2f",
                },
                labels={
                    "Valor_Faturado_Fmt": "Faturamento",
                    "Qtd_Clientes": "Clientes Ativos",
                    "Participacao": "% do Total",
                    "Valor_Faturado": "Faturamento (R$)",
                },
            )
            fig_mapa.update_geos(
                fitbounds="locations",
                visible=False,
                bgcolor="rgba(0,0,0,0)",
            )
            fig_mapa.update_layout(
                title=dict(text="<b>Distribuição Geográfica do Faturamento por UF</b>", font=dict(size=14, color="#000000")),
                margin=dict(l=0, r=0, t=45, b=0),
                height=470,
                paper_bgcolor="rgba(0,0,0,0)",
                coloraxis_colorbar=dict(title="Faturamento (R$)"),
            )
            st.plotly_chart(fig_mapa, use_container_width=True)
        else:
            fig_bar_uf = px.bar(
                df_uf.head(15),
                x="UF",
                y="Valor_Faturado",
                text="Valor_Faturado_Fmt",
                color="Valor_Faturado",
                color_continuous_scale="Blues",
            )
            fig_bar_uf.update_layout(
                title=dict(text="<b>Faturamento por Estado (UF)</b>", font=dict(size=14, color="#000000")),
                template="plotly_white",
                height=470,
            )
            st.plotly_chart(fig_bar_uf, use_container_width=True)

    with col_rank_uf:
        st.markdown("**📊 Ranking de Faturamento por UF**")
        df_uf_rank = df_uf.copy()
        df_uf_rank.index = df_uf_rank.index + 1
        df_uf_rank.index.name = "Pos."
        df_uf_rank["Participacao_Str"] = df_uf_rank["Participacao"].apply(lambda p: f"{p:.2f}%")

        st.dataframe(
            df_uf_rank[["UF", "Valor_Faturado_Fmt", "Qtd_Clientes", "Participacao_Str"]].rename(
                columns={
                    "UF": "Estado (UF)",
                    "Valor_Faturado_Fmt": "Faturamento Total (R$)",
                    "Qtd_Clientes": "Qtd. Clientes",
                    "Participacao_Str": "% Share",
                }
            ),
            use_container_width=True,
            height=430,
        )


def render_tabela_consolidada(df_filtrado: pd.DataFrame, col_fat_ativa: str, col_dev_ativa: str):
    st.markdown("### 📜 Base Consolidada Diária (Produção, Expedição, Faturamento e Frete)")

    if df_filtrado is None or df_filtrado.empty:
        st.info("Sem registros consolidados para o período selecionado.")
        return

    df_show = df_filtrado.copy()
    df_show["Data"] = pd.to_datetime(df_show["DATA"]).dt.strftime("%d/%m/%Y")

    cols_map = {
        "Data": "Data",
        "Notas_Realizadas": "Notas Realizadas (PVs)",
        "Saudavel": "Notas Saudáveis",
        "Backlog": "Backlog",
        "Total_SKUs": "Total SKUs",
        "Total_Expedidos": "Volume Expedido",
    }

    if col_fat_ativa in df_show.columns:
        df_show["Fat_Fmt"] = df_show[col_fat_ativa].apply(_format_brl)
        cols_map["Fat_Fmt"] = "Faturamento (R$)"

    if col_dev_ativa in df_show.columns:
        df_show["Dev_Fmt"] = df_show[col_dev_ativa].apply(_format_brl)
        cols_map["Dev_Fmt"] = "Devoluções (R$)"

    if "Total_Frete" in df_show.columns:
        df_show["Frete_Fmt"] = df_show["Total_Frete"].apply(_format_brl)
        cols_map["Frete_Fmt"] = "Frete Terceirizado (R$)"

    cols_existentes = [c for c in cols_map.keys() if c in df_show.columns]
    st.dataframe(
        df_show[cols_existentes].rename(columns=cols_map),
        use_container_width=True,
        height=480,
    )