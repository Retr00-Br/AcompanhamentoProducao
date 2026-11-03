import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from utils.parser import fmt_brl


def render_graficos_producao(df_filtrado_prod: pd.DataFrame, col_fat_ativa: str, unidade_selecionada: str):

    # -------------------------------------------------------------
    # GRÁFICO 1: PRODUÇÃO (PV) VS FATURAMENTO
    # -------------------------------------------------------------
    st.subheader(f"💵 Produção Diária: Pedidos de Venda (PV) vs. Faturamento ({unidade_selecionada})")

    eixo_x = df_filtrado_prod["Data_Str"].astype(str).tolist()
    y_pvs = df_filtrado_prod["Total_PVs"].astype(float).tolist()
    y_fat = df_filtrado_prod[col_fat_ativa].astype(float).tolist()

    max_pv = max(y_pvs) if y_pvs else 100.0

    fig_fat = go.Figure()
    fig_fat.add_trace(
        go.Bar(
            x=eixo_x,
            y=y_pvs,
            name="PVs",
            marker=dict(color="#0077b6", line=dict(color="#000000", width=1)),
            text=[f"<b>{int(v)}</b>" if v > 0 else "" for v in y_pvs],
            textfont=dict(color="#000000", size=12),
            textposition="outside",
            textangle=0,
            cliponaxis=False,
        )
    )
    fig_fat.add_trace(
        go.Scatter(
            x=eixo_x,
            y=y_fat,
            name="Faturamento",
            mode="lines+markers+text",
            text=[fmt_brl(v) for v in y_fat],
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
        font=dict(color="#000000", size=13, family="Arial"),
        margin=dict(l=60, r=60, t=60, b=60),
        height=620,
        bargap=0.15,
        yaxis=dict(
            title=dict(text="<b>Qtd. Pedidos (PV)</b>", font=dict(size=14)),
            range=[0, max_pv * 1.25] if max_pv > 0 else None,
            tickfont=dict(size=12),
        ),
        yaxis2=dict(
            title=dict(text="<b>Valor Faturado (R$)</b>", font=dict(size=14)),
            overlaying="y",
            side="right",
            showgrid=False,
            tickfont=dict(size=12),
        ),
        xaxis=dict(type="category", tickfont=dict(size=12)),
        legend=dict(orientation="h", y=1.1, x=1, xanchor="right", font=dict(size=13)),
    )
    st.plotly_chart(fig_fat, use_container_width=True)

    # -------------------------------------------------------------
    # GRÁFICO 2: PRODUÇÃO (PV) VS SKUs/LINHAS
    # -------------------------------------------------------------
    st.subheader("📊 Produção Diária: Pedidos de Venda (PV) vs. SKUs/Linhas")
    y_skus = df_filtrado_prod["Total_SKUs"].astype(float).tolist()

    fig_sku = go.Figure()
    fig_sku.add_trace(
        go.Bar(
            x=eixo_x,
            y=y_pvs,
            name="PVs",
            marker=dict(color="#0077b6", line=dict(color="#000000", width=1)),
            text=[f"<b>{int(v)}</b>" if v > 0 else "" for v in y_pvs],
            textfont=dict(color="#000000", size=12),
            textposition="outside",
            textangle=0,
            cliponaxis=False,
        )
    )
    fig_sku.add_trace(
        go.Scatter(
            x=eixo_x,
            y=y_skus,
            name="SKUs/Linhas",
            mode="lines+markers+text",
            text=[f"<b>{int(v)}</b>" if v > 0 else "" for v in y_skus],
            textfont=dict(color="#000000", size=12),
            textposition="top center",
            marker=dict(color="#d97706", size=8),
            line=dict(color="#d97706", width=3),
            yaxis="y2",
        )
    )
    fig_sku.update_layout(
        template="plotly_white",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#000000", size=13, family="Arial"),
        margin=dict(l=60, r=60, t=60, b=60),
        height=620,
        bargap=0.15,
        yaxis=dict(
            title=dict(text="<b>Qtd. Pedidos (PV)</b>", font=dict(size=14)),
            range=[0, max_pv * 1.25] if max_pv > 0 else None,
            tickfont=dict(size=12),
        ),
        yaxis2=dict(
            title=dict(text="<b>Total SKUs/Linhas</b>", font=dict(size=14)),
            overlaying="y",
            side="right",
            showgrid=False,
            tickfont=dict(size=12),
        ),
        xaxis=dict(type="category", tickfont=dict(size=12)),
        legend=dict(orientation="h", y=1.1, x=1, xanchor="right", font=dict(size=13)),
    )
    st.plotly_chart(fig_sku, use_container_width=True)

    # -------------------------------------------------------------
    # GRÁFICO 3: SAUDÁVEL VS BACKLOG
    # -------------------------------------------------------------
    st.subheader("📋 Produção Diária Isolada: Notas Saudáveis vs. Backlog")
    y_saudavel = df_filtrado_prod["SAUDAVEL"].astype(float).tolist()
    y_backlog = df_filtrado_prod["BACKLOG"].astype(float).tolist()

    fig_status = go.Figure()
    fig_status.add_trace(
        go.Bar(
            x=eixo_x,
            y=y_saudavel,
            name="Notas Saudáveis",
            marker=dict(color="#0f9f90", line=dict(color="#000000", width=0.8)),
            text=[f"<b>{int(v)}</b>" if v > 0 else "" for v in y_saudavel],
            textfont=dict(color="#ffffff", size=11),
            textposition="inside",
            textangle=0,
            cliponaxis=False,
        )
    )
    fig_status.add_trace(
        go.Bar(
            x=eixo_x,
            y=y_backlog,
            name="Backlog",
            marker=dict(color="#d9381e", line=dict(color="#000000", width=0.8)),
            text=[f"<b>{int(v)}</b>" if v > 0 else "" for v in y_backlog],
            textfont=dict(color="#ffffff", size=11),
            textposition="inside",
            textangle=0,
            cliponaxis=False,
        )
    )
    fig_status.update_layout(
        template="plotly_white",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#000000", size=13, family="Arial"),
        barmode="stack",
        height=620,
        bargap=0.15,
        yaxis=dict(
            title=dict(text="<b>Quantidade de Pedidos (PV)</b>", font=dict(size=14)),
            tickfont=dict(size=12),
        ),
        xaxis=dict(type="category", tickfont=dict(size=12)),
        legend=dict(orientation="h", y=1.1, x=1, xanchor="right", font=dict(size=13)),
    )
    st.plotly_chart(fig_status, use_container_width=True)

    # -------------------------------------------------------------
    # GRÁFICO 4: PRODUÇÃO VS EXPEDIÇÃO
    # -------------------------------------------------------------
    st.subheader("🚚 Comparativo: Pedidos Produzidos (PV) vs. Expedições")
    y_expedidos = df_filtrado_prod["Total_Expedidos"].astype(float).tolist()
    max_comp = max(max(y_pvs) if y_pvs else 100.0, max(y_expedidos) if y_expedidos else 100.0)

    fig_comp = go.Figure()
    fig_comp.add_trace(
        go.Bar(
            x=eixo_x,
            y=y_pvs,
            name="Produzidos",
            marker=dict(color="#0f9f90", line=dict(color="#000000", width=0.8)),
            text=[f"<b>{int(v)}</b>" if v > 0 else "" for v in y_pvs],
            textfont=dict(color="#000000", size=11),
            textposition="outside",
            textangle=0,
            cliponaxis=False,
        )
    )
    fig_comp.add_trace(
        go.Bar(
            x=eixo_x,
            y=y_expedidos,
            name="Expedidos",
            marker=dict(color="#d9381e", line=dict(color="#000000", width=0.8)),
            text=[f"<b>{int(v)}</b>" if v > 0 else "" for v in y_expedidos],
            textfont=dict(color="#000000", size=11),
            textposition="outside",
            textangle=0,
            cliponaxis=False,
        )
    )
    fig_comp.update_layout(
        template="plotly_white",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#000000", size=13, family="Arial"),
        barmode="group",
        height=620,
        bargap=0.15,
        bargroupgap=0.05,
        yaxis=dict(
            title=dict(text="<b>Quantidade</b>", font=dict(size=14)),
            range=[0, max_comp * 1.25],
            tickfont=dict(size=12),
        ),
        xaxis=dict(type="category", tickfont=dict(size=12)),
        legend=dict(orientation="h", y=1.1, x=1, xanchor="right", font=dict(size=13)),
    )
    st.plotly_chart(fig_comp, use_container_width=True)