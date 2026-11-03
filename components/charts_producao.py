import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from utils.parser import fmt_brl


def render_graficos_producao(df_filtrado_prod: pd.DataFrame, col_fat_ativa: str, unidade_selecionada: str):

    # PURGA DE DIAS ANTERIORES AO INÍCIO DA PRODUÇÃO
    df_prod_ativa = df_filtrado_prod.copy()
    if not df_prod_ativa[df_prod_ativa["Total_PVs"] > 0].empty:
        primeira_data_prod = df_prod_ativa[df_prod_ativa["Total_PVs"] > 0]["DATA"].min()
        df_prod_ativa = df_prod_ativa[df_prod_ativa["DATA"] >= primeira_data_prod].reset_index(drop=True)

    eixo_x = df_prod_ativa["Data_Str"].astype(str).tolist()
    y_pvs = df_prod_ativa["Total_PVs"].astype(float).tolist()
    y_fat = df_prod_ativa[col_fat_ativa].astype(float).tolist()

    max_pv = max(y_pvs) if y_pvs else 100.0
    max_fat = max(y_fat) if y_fat else 1000.0

    # -------------------------------------------------------------
    # GRÁFICO 2: PRODUÇÃO (PV) VS FATURAMENTO
    # -------------------------------------------------------------
    st.subheader(f"💵 Produção Diária: Pedidos de Venda (PV) vs. Faturamento ({unidade_selecionada})")

    fig_fat = go.Figure()
    fig_fat.add_trace(
        go.Bar(
            x=eixo_x,
            y=y_pvs,
            name="PVs",
            marker=dict(color="#0077b6", line=dict(color="#000000", width=1.2)),
            text=[f"<b>{int(v)}</b>" if v > 0 else "" for v in y_pvs],
            textfont=dict(color="#000000", size=12),
            textposition="outside",
            cliponaxis=False,
        )
    )
    fig_fat.add_trace(
        go.Scatter(
            x=eixo_x,
            y=y_fat,
            name="Faturamento",
            mode="lines+markers+text",
            text=[f"<b>{fmt_brl(v)}</b>" for v in y_fat],
            textfont=dict(color="#000000", size=11),
            textposition="top center",
            marker=dict(color="#0a9396", size=8, symbol="circle"),
            line=dict(color="#0a9396", width=2.5),
            yaxis="y2",
        )
    )
    fig_fat.update_layout(
        template="plotly_white",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#000000", size=13, family="Arial"),
        margin=dict(l=60, r=60, t=60, b=60),
        height=580,
        bargap=0.15,
        yaxis=dict(
            title=dict(text="<b>Qtd. Pedidos (PV)</b>", font=dict(size=14, color="#000000")),
            range=[0, max_pv * 1.35] if max_pv > 0 else None,
            tickfont=dict(size=12, color="#000000"),
            showgrid=True,
            gridcolor="#e9ecef",
        ),
        yaxis2=dict(
            title=dict(text="<b>Valor Faturado (R$)</b>", font=dict(size=14, color="#000000")),
            overlaying="y",
            side="right",
            showgrid=False,
            range=[0, max_fat * 1.40] if max_fat > 0 else None,
            tickfont=dict(size=12, color="#000000"),
        ),
        xaxis=dict(type="category", tickfont=dict(size=12, color="#000000")),
        legend=dict(orientation="h", y=1.08, x=1, xanchor="right", font=dict(size=13, color="#000000")),
    )
    st.plotly_chart(fig_fat, use_container_width=True)

    # -------------------------------------------------------------
    # GRÁFICO 3: PRODUÇÃO (PV) VS SKUs/LINHAS (COM SOMA REAL DE DADOSBRUTOS)
    # -------------------------------------------------------------
    st.subheader("📊 Produção Diária: Pedidos de Venda (PV) vs. SKUs/Linhas")
    y_skus = df_prod_ativa["Total_SKUs"].astype(float).tolist()
    max_sku = max(y_skus) if y_skus else 100.0

    fig_sku = go.Figure()
    fig_sku.add_trace(
        go.Bar(
            x=eixo_x,
            y=y_pvs,
            name="PVs",
            marker=dict(color="#0077b6", line=dict(color="#000000", width=1.2)),
            text=[f"<b>{int(v)}</b>" if v > 0 else "" for v in y_pvs],
            textfont=dict(color="#000000", size=12),
            textposition="outside",
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
            textfont=dict(color="#000000", size=11),
            textposition="top center",
            marker=dict(color="#d97706", size=8, symbol="diamond"),
            line=dict(color="#d97706", width=2.5),
            yaxis="y2",
        )
    )
    fig_sku.update_layout(
        template="plotly_white",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#000000", size=13, family="Arial"),
        margin=dict(l=60, r=60, t=60, b=60),
        height=580,
        bargap=0.15,
        yaxis=dict(
            title=dict(text="<b>Qtd. Pedidos (PV)</b>", font=dict(size=14, color="#000000")),
            range=[0, max_pv * 1.35] if max_pv > 0 else None,
            tickfont=dict(size=12, color="#000000"),
            showgrid=True,
            gridcolor="#e9ecef",
        ),
        yaxis2=dict(
            title=dict(text="<b>Total SKUs/Linhas</b>", font=dict(size=14, color="#000000")),
            overlaying="y",
            side="right",
            showgrid=False,
            range=[0, max_sku * 1.35] if max_sku > 0 else None,
            tickfont=dict(size=12, color="#000000"),
        ),
        xaxis=dict(type="category", tickfont=dict(size=12, color="#000000")),
        legend=dict(orientation="h", y=1.08, x=1, xanchor="right", font=dict(size=13, color="#000000")),
    )
    st.plotly_chart(fig_sku, use_container_width=True)

    # -------------------------------------------------------------
    # GRÁFICO 4: SAUDÁVEL VS BACKLOG
    # -------------------------------------------------------------
    st.subheader("📋 Produção Diária Isolada: Notas Saudáveis vs. Backlog")
    y_saudavel = df_prod_ativa["SAUDAVEL"].astype(float).tolist()
    y_backlog = df_prod_ativa["BACKLOG"].astype(float).tolist()

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
            cliponaxis=False,
        )
    )
    fig_status.update_layout(
        template="plotly_white",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#000000", size=13, family="Arial"),
        barmode="stack",
        height=580,
        bargap=0.15,
        yaxis=dict(
            title=dict(text="<b>Quantidade de Pedidos (PV)</b>", font=dict(size=14, color="#000000")),
            tickfont=dict(size=12, color="#000000"),
            showgrid=True,
            gridcolor="#e9ecef",
        ),
        xaxis=dict(type="category", tickfont=dict(size=12, color="#000000")),
        legend=dict(orientation="h", y=1.08, x=1, xanchor="right", font=dict(size=13, color="#000000")),
    )
    st.plotly_chart(fig_status, use_container_width=True)

    # -------------------------------------------------------------
    # GRÁFICO 5: PRODUÇÃO VS EXPEDIÇÃO
    # -------------------------------------------------------------
    st.subheader("🚚 Comparativo: Pedidos Produzidos (PV) vs. Expedições")
    y_expedidos = df_prod_ativa["Total_Expedidos"].astype(float).tolist()
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
            cliponaxis=False,
        )
    )
    fig_comp.update_layout(
        template="plotly_white",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#000000", size=13, family="Arial"),
        barmode="group",
        height=580,
        bargap=0.15,
        bargroupgap=0.05,
        yaxis=dict(
            title=dict(text="<b>Quantidade</b>", font=dict(size=14, color="#000000")),
            range=[0, max_comp * 1.30],
            tickfont=dict(size=12, color="#000000"),
            showgrid=True,
            gridcolor="#e9ecef",
        ),
        xaxis=dict(type="category", tickfont=dict(size=12, color="#000000")),
        legend=dict(orientation="h", y=1.08, x=1, xanchor="right", font=dict(size=13, color="#000000")),
    )
    st.plotly_chart(fig_comp, use_container_width=True)