import pandas as pd
import plotly.graph_objects as go
import streamlit as st


def render_top10_faturamento(df_fat_detalhado: pd.DataFrame, unidade_selecionada: str):
    st.divider()
    st.subheader(f"💎 Ranking Top 10 Clientes por Faturamento Monetário ({unidade_selecionada})")

    if df_fat_detalhado is None or df_fat_detalhado.empty:
        st.info("Sem dados de faturamento para exibição.")
        return

    df_fd10 = df_fat_detalhado.copy()
    if unidade_selecionada != "Todas as Unidades (Geral)" and "Filial" in df_fd10.columns:
        codigo_filial = int(unidade_selecionada.split(" - ")[0])
        df_fd10 = df_fd10[df_fd10["Filial"] == codigo_filial]

    col_cli_10 = (
        "Cliente"
        if "Cliente" in df_fd10.columns
        else ("Nome Fantasia" if "Nome Fantasia" in df_fd10.columns else df_fd10.columns[2])
    )
    col_emissao_10 = (
        "Data"
        if "Data" in df_fd10.columns
        else ("Emissão" if "Emissão" in df_fd10.columns else df_fd10.columns[0])
    )
    col_valor_10 = (
        "R$ Fatur."
        if "R$ Fatur." in df_fd10.columns
        else ("Valor" if "Valor" in df_fd10.columns else df_fd10.columns[-1])
    )

    df_fd10["DATA_STR"] = pd.to_datetime(df_fd10[col_emissao_10], errors="coerce").dt.strftime("%Y-%m-%d")
    datas_disponiveis = sorted(df_fd10["DATA_STR"].dropna().unique())

    col_m, col_d = st.columns([2, 2])
    with col_m:
        modo_top10 = st.radio(
            "Modo de Exibição:",
            ["Por Dia Selecionado", "Acumulado do Período Geral"],
            horizontal=True,
            key="modo_top10_fat",
        )

    if modo_top10 == "Por Dia Selecionado" and datas_disponiveis:
        with col_d:
            data_sel = st.selectbox("Selecione a Data:", datas_disponiveis, index=len(datas_disponiveis) - 1)
        df_top10_filtrado = df_fd10[df_fd10["DATA_STR"] == data_sel]
        titulo = f"Top 10 Clientes no Dia: {data_sel}"
    else:
        df_top10_filtrado = df_fd10
        titulo = "Top 10 Clientes por Faturamento Acumulado"

    df_top10 = (
        df_top10_filtrado.groupby(col_cli_10)[col_valor_10]
        .sum()
        .reset_index(name="Total_Faturado")
        .sort_values("Total_Faturado", ascending=True)
        .tail(10)
    )

    if not df_top10.empty:
        fig_top10 = go.Figure(
            go.Bar(
                y=df_top10[col_cli_10],
                x=df_top10["Total_Faturado"],
                orientation="h",
                marker=dict(color="#118ab2"),
                text=[
                    f"<b>R$ {v:,.2f}</b>".replace(",", "X").replace(".", ",").replace("X", ".")
                    for v in df_top10["Total_Faturado"]
                ],
                textposition="auto",
            )
        )
        fig_top10.update_layout(
            template="plotly_white",
            height=500,
            title=dict(text=f"<b>{titulo}</b>"),
            xaxis=dict(title="<b>Valor Faturado (R$)</b>"),
            yaxis=dict(title="<b>Cliente</b>"),
            margin=dict(l=180, r=40, t=50, b=40),
        )
        st.plotly_chart(fig_top10, use_container_width=True)


def render_tabela_consolidada(df_filtrado: pd.DataFrame, col_fat_ativa: str, col_dev_ativa: str):
    with st.expander("🔍 Visualizar Tabela Consolidada"):
        cols_para_exibir = [
            "DATA",
            "Total_PVs",
            "SAUDAVEL",
            "BACKLOG",
            "Total_SKUs",
            col_fat_ativa,
            col_dev_ativa,
            "Total_Expedidos",
        ]
        if "Total_Frete" in df_filtrado.columns:
            cols_para_exibir.append("Total_Frete")

        st.dataframe(
            df_filtrado[cols_para_exibir],
            use_container_width=True,
        )