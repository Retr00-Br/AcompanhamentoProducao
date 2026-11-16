import urllib.request
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


FILIAL_LABELS = {
    "101": "0101 - Matriz",
    "102": "0102 - Filial RJ",
    "103": "0103 - Filial CP",
    "104": "0104 - Filial SBC",
}


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


def _normalizar_filial(val) -> str:
    s = str(val).strip()
    if s.endswith(".0"):
        s = s[:-2]
    s_clean = s.lstrip("0")
    return FILIAL_LABELS.get(s_clean, f"Filial {s}")


def _filtrar_por_filial_e_mes(
    df_base: pd.DataFrame,
    filial_sel: str,
    mes_sel: str,
) -> pd.DataFrame:
    df_out = df_base.copy()
    if filial_sel != "Todas as Filiais (Acumulado Geral)":
        df_out = df_out[df_out["Filial_Nome"] == filial_sel].copy()
    if mes_sel != "Todos os Meses (Acumulado Geral)":
        df_out = df_out[df_out["Mes_Str"] == mes_sel].copy()
    return df_out


def _plot_ranking_clientes_colunas(
    df_ranking: pd.DataFrame,
    col_valor: str,
    periodo_label: str,
    filial_label: str,
    cor_barra: str = "#1f77b4",
):
    if df_ranking.empty:
        st.info("Nenhum lançamento de cliente encontrado para esta combinação de Filial e Mês.")
        return

    fig_colunas = go.Figure()

    for idx_rank, row_top in df_ranking.iterrows():
        label_cli = row_top["Cliente_Loja_UF_Filial"]
        valor_cli = row_top[col_valor]

        fig_colunas.add_trace(
            go.Bar(
                x=[f"#{idx_rank + 1} {label_cli}"],
                y=[valor_cli],
                name=f"#{idx_rank + 1} {label_cli} ({_format_brl(valor_cli)})",
                marker=dict(line=dict(color="#000000", width=0.8)),
                text=[_format_brl(valor_cli)],
                textposition="outside",
                textfont=dict(size=10, color="#000000", family="Arial Black"),
                cliponaxis=False,
                hovertemplate=(
                    f"<b>#{idx_rank + 1} {label_cli}</b><br>"
                    f"Filial: {filial_label}<br>"
                    f"Período: {periodo_label}<br>"
                    "Faturamento: R$ %{y:,.2f}<extra></extra>"
                ),
            )
        )

    max_y_colunas = df_ranking[col_valor].max() if not df_ranking.empty else 100.0

    fig_colunas.update_layout(
        template="plotly_white",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#000000", size=12, family="Arial"),
        height=560,
        margin=dict(l=50, r=40, t=50, b=120),
        barmode="group",
        showlegend=True,
        xaxis=dict(
            title=dict(text="<b>Cliente (Filial | Loja - UF)</b>", font=dict(size=13, color="#000000")),
            type="category",
            tickangle=-25,
            tickfont=dict(size=10, color="#000000"),
            showgrid=False,
        ),
        yaxis=dict(
            title=dict(text="<b>Faturamento Monetário (R$)</b>", font=dict(size=13, color="#000000")),
            showgrid=True,
            gridcolor="#e9ecef",
            range=[0, max(max_y_colunas * 1.24, 100.0)],
        ),
        legend=dict(
            orientation="v",
            y=1.0,
            x=1.02,
            xanchor="left",
            font=dict(size=11, color="#000000"),
        ),
    )

    st.plotly_chart(fig_colunas, use_container_width=True)


def render_top10_faturamento(df_fat_detalhado: pd.DataFrame, unidade_selecionada: str = "Todas as Unidades (Geral)"):
    st.markdown("---")
    st.markdown("### 🏆 Top 10 Clientes por Faturamento Monetário & Distribuição Geográfica (UF)")

    if df_fat_detalhado is None or df_fat_detalhado.empty:
        st.info("Sem dados detalhados por cliente na aba 'Faturamento por cliente'.")
        return

    df = df_fat_detalhado.copy()
    df.columns = [str(c).strip() for c in df.columns]

    col_valor = next((c for c in df.columns if "FATUR" in c.upper() or "VALOR" in c.upper()), df.columns[-1])
    df[col_valor] = pd.to_numeric(df[col_valor], errors="coerce").fillna(0.0)

    if "Filial" in df.columns:
        df["Filial_Nome"] = df["Filial"].apply(_normalizar_filial)
        df["Filial_Cod"] = df["Filial"].astype(str).str.replace(".0", "", regex=False).str.strip().str.zfill(4)
    else:
        df["Filial_Nome"] = "0101 - Matriz"
        df["Filial_Cod"] = "0101"

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

    if "Mês" in df.columns:
        df["Mes_Dt"] = pd.to_datetime(df["Mês"], errors="coerce")
        df["Mes_Str"] = df["Mes_Dt"].dt.strftime("%Y-%m")
    else:
        df["Mes_Str"] = "Total"

    df["Cliente_Loja_UF_Filial"] = (
        df["Cliente"] + " [" + df["Filial_Cod"] + " | Lj " + df["Loja"] + " - " + df["UF"] + "]"
    )

    meses_ordenados = sorted(df["Mes_Str"].dropna().unique().tolist())
    filiais_disponiveis = sorted(df["Filial_Nome"].dropna().unique().tolist())

    opcoes_filiais_cli = ["Todas as Filiais (Acumulado Geral)"] + filiais_disponiveis
    opcoes_meses_cli = ["Todos os Meses (Acumulado Geral)"] + meses_ordenados

    # =========================================================================
    # 1. RANKING TOP 10 CLIENTES (MAIOR FATURAMENTO) POR FILIAL & MÊS
    # =========================================================================
    st.markdown("#### 📊 Ranking Top 10 Clientes — Maior Faturamento (Diferenciado por Filial, Loja & UF)")

    col_f_top1, col_f_top2 = st.columns(2)
    with col_f_top1:
        filial_top10_sel = st.selectbox(
            "🏢 Filtrar Clientes por Filial (Top 10):",
            options=opcoes_filiais_cli,
            index=0,
            key="select_filial_top10_colunas",
        )
    with col_f_top2:
        mes_top10_sel = st.selectbox(
            "📅 Selecione o Mês (Top 10):",
            options=opcoes_meses_cli,
            index=0,
            key="select_mes_top10_colunas",
        )

    df_top10_base = _filtrar_por_filial_e_mes(df, filial_top10_sel, mes_top10_sel)

    ranking_top10 = (
        df_top10_base.groupby(["Cliente_Loja_UF_Filial", "Filial_Nome", "Cliente", "Loja", "UF"], as_index=False)[col_valor]
        .sum()
        .sort_values(col_valor, ascending=False)
        .head(10)
        .reset_index(drop=True)
    )

    _plot_ranking_clientes_colunas(ranking_top10, col_valor, mes_top10_sel, filial_top10_sel)

    # =========================================================================
    # 2. RANKING BOTTOM 10 CLIENTES (MENOR FATURAMENTO > R$ 0,00) POR FILIAL & MÊS
    # =========================================================================
    st.markdown("---")
    st.markdown("#### 📉 Ranking Bottom 10 Clientes — Menor Faturamento Monetário (Diferenciado por Filial, Loja & UF)")

    col_f_bot1, col_f_bot2 = st.columns(2)
    with col_f_bot1:
        filial_bot10_sel = st.selectbox(
            "🏢 Filtrar Clientes por Filial (Menor Faturamento):",
            options=opcoes_filiais_cli,
            index=0,
            key="select_filial_bot10_colunas",
        )
    with col_f_bot2:
        mes_bot10_sel = st.selectbox(
            "📅 Selecione o Mês (Menor Faturamento):",
            options=opcoes_meses_cli,
            index=0,
            key="select_mes_bot10_colunas",
        )

    df_bot10_base = _filtrar_por_filial_e_mes(df, filial_bot10_sel, mes_bot10_sel)

    ranking_bot10 = (
        df_bot10_base.groupby(["Cliente_Loja_UF_Filial", "Filial_Nome", "Cliente", "Loja", "UF"], as_index=False)[col_valor]
        .sum()
    )
    ranking_bot10 = (
        ranking_bot10[ranking_bot10[col_valor] > 0]
        .sort_values(col_valor, ascending=True)
        .head(10)
        .reset_index(drop=True)
    )

    _plot_ranking_clientes_colunas(ranking_bot10, col_valor, mes_bot10_sel, filial_bot10_sel)

    # =========================================================================
    # 3. MAPA DO BRASIL POR UF + RANKING DE FATURAMENTO POR UF (POR FILIAL & MÊS)
    # =========================================================================
    st.markdown("---")
    st.markdown("#### 🗺️ Mapa de Faturamento por Estado (UF) & Ranking Regional")

    col_uf_f1, col_uf_f2 = st.columns(2)
    with col_uf_f1:
        filial_uf_sel = st.selectbox(
            "🏢 Filtrar Mapa & Ranking por Filial:",
            options=opcoes_filiais_cli,
            index=0,
            key="filtro_filial_uf_mapa",
        )
    with col_uf_f2:
        mes_uf_sel = st.selectbox(
            "📅 Filtrar Competência (Mapa & Ranking por UF):",
            options=opcoes_meses_cli,
            index=0,
            key="filtro_mes_uf_mapa",
        )

    df_uf_base = _filtrar_por_filial_e_mes(df, filial_uf_sel, mes_uf_sel)

    total_faturado_geral = df_uf_base[col_valor].sum()

    df_uf = (
        df_uf_base[df_uf_base["UF"].str.len() == 2]
        .groupby("UF", as_index=False)
        .agg(
            Valor_Faturado=(col_valor, "sum"),
            Qtd_Clientes=("Cliente", "nunique"),
            Filiais_Ativas=("Filial_Cod", lambda x: ", ".join(sorted(set(x)))),
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
                    "Filiais_Ativas": True,
                    "Participacao": ":.2f",
                },
                labels={
                    "Valor_Faturado_Fmt": "Faturamento",
                    "Qtd_Clientes": "Clientes Ativos",
                    "Filiais_Ativas": "Filiais",
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
            df_uf_rank[["UF", "Filiais_Ativas", "Valor_Faturado_Fmt", "Qtd_Clientes", "Participacao_Str"]].rename(
                columns={
                    "UF": "Estado (UF)",
                    "Filiais_Ativas": "Filiais",
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