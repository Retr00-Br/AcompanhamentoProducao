import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from utils.parser import fmt_brl


def render_secao_faturamento(df_filtrado: pd.DataFrame, unidade_selecionada: str):
    st.markdown("---")
    st.markdown(f"### 📈 Faturamento Diário x Devoluções — {unidade_selecionada}")

    if df_filtrado.empty:
        st.info("Sem dados de faturamento para o período selecionado.")
        return

    col_fat = f"{unidade_selecionada}_Fat"
    col_dev = f"{unidade_selecionada}_Dev"

    if col_fat not in df_filtrado.columns or col_dev not in df_filtrado.columns:
        st.info("Dados de faturamento indisponíveis para esta unidade.")
        return

    df_chart = df_filtrado.copy()

    # Garantir que devoluções fiquem sempre positivas (abs) no gráfico para não inverter o eixo Y2
    df_chart["Dev_Positiva"] = df_chart[col_dev].abs()

    eixo_x = df_chart["Data_Str"].tolist()
    y_fat = df_chart[col_fat].tolist()
    y_dev = df_chart["Dev_Positiva"].tolist()

    max_fat = max(y_fat) if y_fat else 1000.0
    max_dev = max(y_dev) if y_dev else 1000.0

    fig = go.Figure()

    # Barras de Faturamento Monetário
    fig.add_trace(
        go.Bar(
            x=eixo_x,
            y=y_fat,
            name="Faturamento (R$)",
            marker=dict(color="#0077b6", line=dict(color="#000000", width=1.0)),
            text=[fmt_brl(v) if v > 0 else "R$ 0,00" for v in y_fat],
            textfont=dict(color="#000000", size=10, family="Arial"),
            textposition="outside",
            cliponaxis=False,
        )
    )

    # Linha de Devoluções (Positiva para leitura limpa no eixo Y2)
    fig.add_trace(
        go.Scatter(
            x=eixo_x,
            y=y_dev,
            name="Devoluções (R$)",
            mode="lines+markers",
            marker=dict(color="#000000", size=7, symbol="square"),
            line=dict(color="#000000", width=2.0),
            hovertemplate="<b>Data: %{x}</b><br>Devolução: R$ %{y:,.2f}<extra></extra>",
            yaxis="y2",
        )
    )

    fig.update_layout(
        template="plotly_white",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#000000", size=12, family="Arial"),
        margin=dict(l=50, r=60, t=40, b=60),
        height=540,
        bargap=0.20,
        yaxis=dict(
            title=dict(text="<b>Faturamento Monetário (R$)</b>", font=dict(size=13, color="#000000")),
            tickprefix="R$ ",
            showgrid=True,
            gridcolor="#e9ecef",
            range=[0, max_fat * 1.30],
        ),
        yaxis2=dict(
            title=dict(text="<b>Devoluções (R$)</b>", font=dict(size=13, color="#000000")),
            overlaying="y",
            side="right",
            tickprefix="R$ ",
            showgrid=False,
            range=[0, max(max_dev * 1.40, 1000.0)],  # Escala limpa e positiva
        ),
        xaxis=dict(type="category", tickfont=dict(size=11, color="#000000")),
        legend=dict(orientation="h", y=1.12, x=1, xanchor="right", font=dict(size=12, color="#000000")),
    )

    st.plotly_chart(fig, use_container_width=True)