import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from utils.parser import fmt_brl


def render_secao_faturamento(df_filtrado: pd.DataFrame, unidade_selecionada: str):
    col_fat_ativa = f"{unidade_selecionada}_Fat"
    col_dev_ativa = f"{unidade_selecionada}_Dev"

    fat_total = df_filtrado[col_fat_ativa].sum() if col_fat_ativa in df_filtrado.columns else 0.0
    dev_total = df_filtrado[col_dev_ativa].sum() if col_dev_ativa in df_filtrado.columns else 0.0

    dias_com_fat = len(df_filtrado[df_filtrado[col_fat_ativa] > 0])
    divisor = dias_com_fat if dias_com_fat > 0 else 1
    media_fat = fat_total / divisor
    media_dev = dev_total / divisor

    st.markdown(f"### 💰 Faturamento & Devoluções ({unidade_selecionada})")
    kf1, kf2, kf3, kf4 = st.columns(4)
    
    kf1.metric("💵 Faturamento Total", f"R$ {fat_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    kf2.metric("🔴 Total Devoluções", f"R$ {dev_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    kf3.metric("📊 Média Faturada/Dia", f"R$ {media_fat:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    kf4.metric("📉 Média Devolução/Dia", f"R$ {media_dev:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    if not df_filtrado.empty:
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.08,
            row_heights=[0.7, 0.3],
            subplot_titles=("Faturamento Diário (R$)", "Devoluções Diárias (R$)")
        )

        labels_fat = [fmt_brl(v) for v in df_filtrado[col_fat_ativa]]
        labels_dev = [fmt_brl(v) if v > 0 else "" for v in df_filtrado[col_dev_ativa]]

        # Painel 1: Faturamento (Barras)
        fig.add_trace(
            go.Bar(
                x=df_filtrado["Data_Str"],
                y=df_filtrado[col_fat_ativa],
                name="Faturamento",
                marker=dict(color="#0077b6", line=dict(color="#000000", width=1)),
                text=labels_fat,
                textfont=dict(color="#000000", size=11),
                textposition="outside",
                cliponaxis=False,
            ),
            row=1, col=1
        )

        # Painel 2: Devoluções (Linha)
        fig.add_trace(
            go.Scatter(
                x=df_filtrado["Data_Str"],
                y=df_filtrado[col_dev_ativa],
                name="Devoluções",
                mode="lines+markers+text",
                marker=dict(color="#d90429", size=6),
                line=dict(color="#d90429", width=2),
                text=labels_dev,
                textfont=dict(color="#d90429", size=11),
                textposition="top center",
                cliponaxis=False,
            ),
            row=2, col=1
        )

        max_fat = df_filtrado[col_fat_ativa].max() if not df_filtrado[col_fat_ativa].empty else 1000
        max_dev = df_filtrado[col_dev_ativa].max() if not df_filtrado[col_dev_ativa].empty else 1000

        fig.update_yaxes(range=[0, max_fat * 1.25], row=1, col=1, tickprefix="R$ ")
        fig.update_yaxes(range=[0, max_dev * 1.35], row=2, col=1, tickprefix="R$ ")
        
        fig.update_layout(
            template="plotly_white",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#000000", size=13, family="Arial"),
            margin=dict(l=60, r=60, t=50, b=60),
            height=680,
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)

    st.divider()