import pandas as pd
import plotly.graph_objects as go
import streamlit as st


def render_top10_faturamento(df_fat_detalhado: pd.DataFrame, unidade_selecionada: str):
    st.markdown("---")
    st.markdown("### 🏆 Top Clientes por Faturamento Monetário")

    if df_fat_detalhado is None or df_fat_detalhado.empty:
        st.info("Sem dados detalhados de faturamento por cliente.")
        return

    df_cli = df_fat_detalhado.copy()

    col_cli = "Cliente" if "Cliente" in df_cli.columns else df_cli.columns[2]
    col_val = "R$ Fatur." if "R$ Fatur." in df_cli.columns else ("Faturamento" if "Faturamento" in df_cli.columns else df_cli.columns[3])
    col_mes = "Mês" if "Mês" in df_cli.columns else df_cli.columns[0]

    df_cli[col_mes] = pd.to_datetime(df_cli[col_mes], errors="coerce")
    df_cli["Mes_Str"] = df_cli[col_mes].dt.strftime("%Y-%m")
    df_cli[col_val] = pd.to_numeric(df_cli[col_val], errors="coerce").fillna(0.0)

    meses_disponiveis = sorted([m for m in df_cli["Mes_Str"].dropna().unique()])
    opcoes_visao = ["Acumulado Geral"] + meses_disponiveis

    col_sel1, col_sel2 = st.columns([2, 3])
    with col_sel1:
        visao_selecionada = st.selectbox(
            "📅 Selecione a Visualização dos Clientes:",
            opcoes_visao,
            index=0,
            key="top_clientes_visao_mes_sel",
        )

    if visao_selecionada == "Acumulado Geral":
        df_top = df_cli.groupby(col_cli)[col_val].sum().reset_index()
        titulo_grafico = "Top 10 Clientes - Acumulado Geral"
    else:
        df_top = df_cli[df_cli["Mes_Str"] == visao_selecionada].groupby(col_cli)[col_val].sum().reset_index()
        titulo_grafico = f"Top 10 Clientes - Mês {visao_selecionada}"

    df_top = df_top.sort_values(by=col_val, ascending=False).head(10).reset_index(drop=True)

    if df_top.empty:
        st.info("Nenhum registro encontrado para a opção selecionada.")
        return

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=df_top[col_val],
            y=df_top[col_cli],
            orientation="h",
            marker=dict(color="#0077b6", line=dict(color="#000000", width=1.0)),
            text=[f"<b>R$ {v:,.2f}</b>".replace(",", "X").replace(".", ",").replace("X", ".") for v in df_top[col_val]],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="<b>Cliente: %{y}</b><br>Faturamento: R$ %{x:,.2f}<extra></extra>",
        )
    )

    max_val = df_top[col_val].max()

    fig.update_layout(
        title=dict(text=f"<b>{titulo_grafico}</b>", font=dict(size=14, color="#000000")),
        template="plotly_white",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#000000", size=11, family="Arial"),
        margin=dict(l=220, r=120, t=40, b=40),
        height=520,
        xaxis=dict(
            title=dict(text="<b>Faturamento Monetário (R$)</b>", font=dict(size=12, color="#000000")),
            showgrid=True,
            gridcolor="#e9ecef",
            range=[0, max_val * 1.30],
        ),
        yaxis=dict(autorange="reversed", tickfont=dict(size=11, color="#000000")),
    )

    st.plotly_chart(fig, use_container_width=True)


def render_tabela_consolidada(df_filtrado: pd.DataFrame, col_fat_ativa: str, col_dev_ativa: str):
    st.markdown("### 📜 Tabela Consolidada Operacional Diária")

    if df_filtrado is None or df_filtrado.empty:
        st.info("Sem dados para exibição na tabela.")
        return

    df_tb = df_filtrado.copy()
    cols_exibicao = ["DATA", "Total_PVs", "Saudavel", "Backlog", "Total_SKUs", "Total_Expedidos"]

    if col_fat_ativa in df_tb.columns:
        cols_exibicao.append(col_fat_ativa)
    if col_dev_ativa in df_tb.columns:
        cols_exibicao.append(col_dev_ativa)
    if "Total_Frete" in df_tb.columns:
        cols_exibicao.append("Total_Frete")

    cols_existentes = [c for c in cols_exibicao if c in df_tb.columns]
    df_show = df_tb[cols_existentes].copy()
    df_show["DATA"] = df_show["DATA"].dt.strftime("%d/%m/%Y")

    st.dataframe(df_show, use_container_width=True)