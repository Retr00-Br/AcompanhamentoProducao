import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from utils.parser import fmt_brl


def render_top10_faturamento(df_fat_detalhado: pd.DataFrame, unidade_selecionada: str):
    st.markdown("---")
    st.markdown("### 🏆 Top Clientes por Faturamento Monetário")

    if df_fat_detalhado is None or df_fat_detalhado.empty:
        st.info("Dados de faturamento por cliente indisponíveis.")
        return

    df_cli = df_fat_detalhado.copy()
    colunas_3 = [c for c in ["Filial", "Cliente", "R$ Fatur."] if c in df_cli.columns]
    df_cli = df_cli[colunas_3].copy()

    if unidade_selecionada != "Todas as Unidades (Geral)":
        cod_filial = unidade_selecionada.split("-")[0].strip()
        df_cli = df_cli[df_cli["Filial"].astype(str).str.contains(cod_filial, na=False)]

    if df_cli.empty:
        st.info("Nenhum registro para a filial selecionada.")
        return

    # Agrupar por cliente e pegar os 12 maiores acumulados
    df_chart_cli = (
        df_cli.groupby("Cliente")["R$ Fatur."]
        .sum()
        .reset_index()
        .sort_values(by="R$ Fatur.", ascending=True)
        .tail(12)
    )

    # Gráfico de barras horizontais limpo e legível
    fig_cli = go.Figure(
        go.Bar(
            y=df_chart_cli["Cliente"],
            x=df_chart_cli["R$ Fatur."],
            orientation="h",
            marker=dict(color="#0077b6", line=dict(color="#000000", width=1.0)),
            text=[fmt_brl(v) for v in df_chart_cli["R$ Fatur."]],
            textfont=dict(color="#000000", size=11, family="Arial Black"),
            textposition="outside",
            cliponaxis=False,
        )
    )

    fig_cli.update_layout(
        template="plotly_white",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#000000", size=12, family="Arial"),
        margin=dict(l=180, r=90, t=30, b=40),
        height=550,
        xaxis=dict(
            title=dict(text="<b>Faturamento Monetário (R$)</b>", font=dict(size=13, color="#000000")),
            tickprefix="R$ ",
            showgrid=True,
            gridcolor="#e9ecef",
            range=[0, max(df_chart_cli["R$ Fatur."]) * 1.25],
        ),
        yaxis=dict(type="category", tickfont=dict(size=11, color="#000000")),
    )

    st.plotly_chart(fig_cli, use_container_width=True)


def render_tabela_consolidada(df_filtrado: pd.DataFrame, col_fat_ativa: str, col_dev_ativa: str):
    st.markdown("---")
    st.markdown("### 📑 Tabela Consolidada Diária de Operações")

    if df_filtrado is empty if isinstance(df_filtrado, pd.DataFrame) else True:
        st.info("Sem registros para exibição da tabela consolidada.")
        return

    if df_filtrado.empty:
        st.info("Sem registros para exibição da tabela consolidada.")
        return

    df_tab = df_filtrado.copy()
    df_tab["Data"] = df_tab["DATA"].dt.strftime("%d/%m/%Y")

    cols = ["Data"]
    if col_fat_ativa in df_tab.columns:
        df_tab["Faturamento (R$)"] = df_tab[col_fat_ativa].apply(fmt_brl)
        cols.append("Faturamento (R$)")
    if col_dev_ativa in df_tab.columns:
        df_tab["Devoluções (R$)"] = df_tab[col_dev_ativa].apply(fmt_brl)
        cols.append("Devoluções (R$)")
    if "Total_PVs" in df_tab.columns:
        df_tab["PVs"] = df_tab["Total_PVs"].fillna(0).astype(int)
        cols.append("PVs")
    if "Total_Expedidos" in df_tab.columns:
        df_tab["Expedidos"] = df_tab["Total_Expedidos"].fillna(0).astype(int)
        cols.append("Expedidos")
    if "Total_Frete" in df_tab.columns:
        df_tab["Frete (R$)"] = df_tab["Total_Frete"].apply(fmt_brl)
        cols.append("Frete (R$)")

    st.dataframe(
        df_tab[cols],
        use_container_width=True,
        hide_index=True,
        height=min(500, len(df_tab) * 38 + 40),
    )