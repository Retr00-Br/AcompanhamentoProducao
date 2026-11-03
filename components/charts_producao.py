import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from utils.parser import fmt_brl


def render_graficos_producao(df_filtrado_prod: pd.DataFrame, col_fat_ativa: str, unidade_selecionada: str):
    # Gráfico 1: PVs vs Faturamento
    st.subheader(f"💵 Produção Diária: Pedidos de Venda (PV) vs. Faturamento ({unidade_selecionada})")
    fig_fat = go.Figure()
    fig_fat.add_trace(
        go.Bar(
            x=df_filtrado_prod["Data_Str"],
            y=df_filtrado_prod["Total_PVs"],
            name="PVs",
            marker=dict(color="#0077b6", line=dict(color="#000000", width=1)),
            text=[f"<b>{int(v)}</b>" for v in df_filtrado_prod["Total_PVs"]],
            textfont=dict(color="#ffffff", size=13),
            textposition="auto",
        )
    )
    fig_fat.add_trace(
        go.Scatter(
            x=df_filtrado_prod["Data_Str"],
            y=df_filtrado_prod[col_fat_ativa],
            name="Faturamento",
            mode="lines+markers+text",
            text=[fmt_brl(v) for v in df_filtrado_prod[col_fat_ativa]],
            textfont=dict(color="#000000", size=12),
            textposition="top center",
            marker=dict(color="#2ec4b6", size=8),
            line=dict(color="#2ec4b6", width=3),
            yaxis="y2",
        )
    )
    fig_fat.update_layout(
        template="plotly_white",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#000000", size=14),
        margin=dict(l=60, r=60, t=60, b=60),
        height=550,
        yaxis=dict(title="<b>Qtd. Pedidos (PV)</b>"),
        yaxis2=dict(title="<b>Valor Faturado (R$)</b>", overlaying="y", side="right", showgrid=False),
        xaxis=dict(type="category"),
        legend=dict(orientation="h", y=1.1, x=1, xanchor="right"),
    )
    st.plotly_chart(fig_fat, use_container_width=True)

    # Gráfico 2: Saudável vs Backlog
    st.subheader("📋 Produção Diária Isolada: Notas Saudáveis vs. Backlog")
    fig_status = go.Figure()
    fig_status.add_trace(
        go.Bar(
            x=df_filtrado_prod["Data_Str"],
            y=df_filtrado_prod["SAUDAVEL"],
            name="Notas Saudáveis",
            marker=dict(color="#0f9f90"),
            text=[f"<b>{int(v)}</b>" if v > 0 else "" for v in df_filtrado_prod["SAUDAVEL"]],
            textposition="auto",
        )
    )
    fig_status.add_trace(
        go.Bar(
            x=df_filtrado_prod["Data_Str"],
            y=df_filtrado_prod["BACKLOG"],
            name="Backlog",
            marker=dict(color="#d9381e"),
            text=[f"<b>{int(v)}</b>" if v > 0 else "" for v in df_filtrado_prod["BACKLOG"]],
            textposition="auto",
        )
    )
    fig_status.update_layout(
        template="plotly_white",
        barmode="stack",
        height=550,
        yaxis=dict(title="<b>Quantidade de Pedidos (PV)</b>"),
        xaxis=dict(type="category"),
        legend=dict(orientation="h", y=1.1, x=1, xanchor="right"),
    )
    st.plotly_chart(fig_status, use_container_width=True)

    # Gráfico 3: Produção vs Expedição
    st.subheader("🚚 Comparativo: Pedidos Produzidos (PV) vs. Expedições")
    fig_comp = go.Figure()
    fig_comp.add_trace(
        go.Bar(
            x=df_filtrado_prod["Data_Str"],
            y=df_filtrado_prod["Total_PVs"],
            name="Produzidos",
            marker=dict(color="#0f9f90"),
            text=[f"<b>{int(v)}</b>" for v in df_filtrado_prod["Total_PVs"]],
            textposition="auto",
        )
    )
    fig_comp.add_trace(
        go.Bar(
            x=df_filtrado_prod["Data_Str"],
            y=df_filtrado_prod["Total_Expedidos"],
            name="Expedidos",
            marker=dict(color="#d9381e"),
            text=[f"<b>{int(v)}</b>" for v in df_filtrado_prod["Total_Expedidos"]],
            textposition="auto",
        )
    )
    fig_comp.update_layout(
        template="plotly_white",
        barmode="group",
        height=550,
        yaxis=dict(title="<b>Quantidade</b>"),
        xaxis=dict(type="category"),
        legend=dict(orientation="h", y=1.1, x=1, xanchor="right"),
    )
    st.plotly_chart(fig_comp, use_container_width=True)