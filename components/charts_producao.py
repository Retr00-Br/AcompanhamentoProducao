import pandas as pd
import plotly.graph_objects as go
import streamlit as st


def render_graficos_producao(df_filtrado: pd.DataFrame, col_fat_ativa: str, unidade_selecionada: str):
    st.markdown("---")
    st.markdown("### 📋 Produção Diária Isolada: Notas Saudáveis vs. Backlog")

    if df_filtrado is None or df_filtrado.empty:
        st.info("Sem registros de produção para o período selecionado.")
        return

    # 🔒 FILTRO DE CORTE: Considera estritamente a partir do dia 07/10/2026
    dt_corte = pd.to_datetime("2026-10-07")
    df_chart = df_filtrado[df_filtrado["DATA"] >= dt_corte].copy().sort_values("DATA").reset_index(drop=True)

    if df_chart.empty:
        st.info("Sem dados de Saudável e Backlog para o período selecionado (Lançamentos iniciam em 07/10).")
        return

    df_chart["Data_Str"] = df_chart["DATA"].dt.strftime("%d/%m")

    y_saudavel = [int(v) for v in df_chart.get("Saudavel", pd.Series([0] * len(df_chart))).fillna(0)]
    y_backlog = [int(v) for v in df_chart.get("Backlog", pd.Series([0] * len(df_chart))).fillna(0)]
    eixo_x = df_chart["Data_Str"].tolist()

    max_val = max(max(y_saudavel, default=10), max(y_backlog, default=10))

    fig = go.Figure()

    # Barras de Backlog
    fig.add_trace(
        go.Bar(
            x=eixo_x,
            y=y_backlog,
            name="Backlog",
            marker=dict(color="#c0392b", line=dict(color="#000000", width=1.0)),
            text=[f"<b>{v}</b>" if v > 0 else "" for v in y_backlog],
            textfont=dict(color="#000000", size=11, family="Arial Black"),
            textposition="outside",
            cliponaxis=False,
            hovertemplate="<b>Data: %{x}</b><br>Backlog: %{y}<extra></extra>",
        )
    )

    # Barras de Notas Saudáveis
    fig.add_trace(
        go.Bar(
            x=eixo_x,
            y=y_saudavel,
            name="Notas Saudáveis",
            marker=dict(color="#16a085", line=dict(color="#000000", width=1.0)),
            text=[f"<b>{v}</b>" if v > 0 else "" for v in y_saudavel],
            textfont=dict(color="#000000", size=11, family="Arial Black"),
            textposition="outside",
            cliponaxis=False,
            hovertemplate="<b>Data: %{x}</b><br>Saudável: %{y}<extra></extra>",
        )
    )

    fig.update_layout(
        template="plotly_white",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#000000", size=12, family="Arial"),
        margin=dict(l=50, r=50, t=50, b=60),
        height=520,
        barmode="group",
        bargap=0.20,
        yaxis=dict(
            title=dict(text="<b>Quantidade de Pedidos (PV)</b>", font=dict(size=13, color="#000000")),
            showgrid=True,
            gridcolor="#e9ecef",
            range=[0, max_val * 1.35],
        ),
        xaxis=dict(type="category", tickfont=dict(size=11, color="#000000")),
        legend=dict(orientation="h", y=1.12, x=1, xanchor="right", font=dict(size=12, color="#000000")),
    )

    st.plotly_chart(fig, use_container_width=True)