import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from utils.parser import fmt_brl


def render_secao_faturamento(df_filtrado: pd.DataFrame, unidade_selecionada: str):
    st.markdown("### 💵 Evolução do Faturamento & Devoluções")

    col_fat = f"{unidade_selecionada}_Fat"
    col_dev = f"{unidade_selecionada}_Dev"

    if df_filtrado.empty or col_fat not in df_filtrado.columns:
        st.info("Sem dados de faturamento para o período selecionado.")
        return

    df_fat_ativo = df_filtrado.copy()

    if not df_fat_ativo[df_fat_ativo[col_fat] > 0].empty:
        primeira_data = df_fat_ativo[df_fat_ativo[col_fat] > 0]["DATA"].min()
        df_fat_ativo = df_fat_ativo[df_fat_ativo["DATA"] >= primeira_data].reset_index(drop=True)

    eixo_x = df_fat_ativo["Data_Str"].astype(str).tolist()
    y_fat = df_fat_ativo[col_fat].astype(float).tolist()
    y_dev = df_fat_ativo[col_dev].astype(float).tolist()

    max_fat = max(y_fat) if y_fat else 1000.0
    max_dev = max(y_dev) if y_dev else 1000.0

    fig_fat_dev = go.Figure()

    # Barras de Faturamento Monetário
    fig_fat_dev.add_trace(
        go.Bar(
            x=eixo_x,
            y=y_fat,
            name="Faturamento (R$)",
            marker=dict(color="#0077b6", line=dict(color="#000000", width=1.0)),
            text=[fmt_brl(v) for v in y_fat],
            textfont=dict(color="#000000", size=11, family="Arial"),
            textposition="outside",
            cliponaxis=False,
        )
    )

    # Linha de Devoluções (PRETA - ELEVADA NO EIXO Y2 PARA EVITAR SOBREPOSIÇÃO)
    fig_fat_dev.add_trace(
        go.Scatter(
            x=eixo_x,
            y=y_dev,
            name="Devoluções (R$)",
            mode="lines+markers+text",
            marker=dict(color="#000000", size=7, symbol="square"),
            line=dict(color="#000000", width=2.2),
            text=[f"<b>R$ {v:,.0f}</b>" if v > 0 else "" for v in y_dev],
            textfont=dict(color="#000000", size=10, family="Arial"),
            textposition="top center",
            yaxis="y2",
        )
    )

    fig_fat_dev.update_layout(
        template="plotly_white",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#000000", size=13, family="Arial"),
        margin=dict(l=65, r=65, t=75, b=65),
        height=580,
        bargap=0.15,
        yaxis=dict(
            title=dict(text="<b>Faturamento Monetário (R$)</b>", font=dict(size=14, color="#000000")),
            tickprefix="R$ ",
            showgrid=True,
            gridcolor="#e9ecef",
            range=[0, max_fat * 1.35] if max_fat > 0 else None,
            tickfont=dict(size=12, color="#000000"),
        ),
        yaxis2=dict(
            title=dict(text="<b>Devoluções (R$)</b>", font=dict(size=14, color="#000000")),
            overlaying="y",
            side="right",
            showgrid=False,
            range=[0, max_dev * 2.80] if max_dev > 0 else None,  # Expansão para projetar a linha no topo limpo
            tickfont=dict(size=12, color="#000000"),
        ),
        xaxis=dict(type="category", tickfont=dict(size=12, color="#000000")),
        legend=dict(orientation="h", y=1.10, x=1, xanchor="right", font=dict(size=13, color="#000000")),
    )

    st.plotly_chart(fig_fat_dev, use_container_width=True)