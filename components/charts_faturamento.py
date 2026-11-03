import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from utils.parser import fmt_brl


def render_secao_faturamento(df_filtrado: pd.DataFrame, unidade_selecionada: str):
    col_fat_ativa = f"{unidade_selecionada}_Fat"
    col_dev_ativa = f"{unidade_selecionada}_Dev"

    fat_total = float(df_filtrado[col_fat_ativa].sum()) if col_fat_ativa in df_filtrado.columns else 0.0
    dev_total = float(df_filtrado[col_dev_ativa].sum()) if col_dev_ativa in df_filtrado.columns else 0.0

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
        fig_fat_solo = go.Figure()

        eixo_x = df_filtrado["Data_Str"].astype(str).tolist()
        y_fat = df_filtrado[col_fat_ativa].astype(float).tolist()
        y_dev = df_filtrado[col_dev_ativa].astype(float).tolist()

        labels_fat = [fmt_brl(v) for v in y_fat]
        labels_dev = [fmt_brl(v) if v > 0 else "" for v in y_dev]

        max_fat = max(y_fat) if y_fat else 1000.0
        max_dev = max(y_dev) if y_dev else 1000.0

        # Barras de Faturamento
        fig_fat_solo.add_trace(
            go.Bar(
                x=eixo_x,
                y=y_fat,
                name="Faturamento (R$)",
                marker=dict(color="#0077b6", line=dict(color="#000000", width=1.0)),
                text=labels_fat,
                textfont=dict(color="#000000", size=11),
                textposition="outside",
                textangle=0,
                cliponaxis=False,
            )
        )

        # Linha de Devoluções
        fig_fat_solo.add_trace(
            go.Scatter(
                x=eixo_x,
                y=y_dev,
                name="Devoluções (R$)",
                mode="lines+markers+text",
                marker=dict(color="#d90429", size=7, symbol="circle"),
                line=dict(color="#d90429", width=2.0),
                text=labels_dev,
                textfont=dict(color="#d90429", size=11),
                textposition="bottom center",
                yaxis="y2",
            )
        )

        fig_fat_solo.update_layout(
            template="plotly_white",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#000000", size=13, family="Arial"),
            margin=dict(l=65, r=65, t=75, b=65),
            height=640,
            bargap=0.15,
            yaxis=dict(
                title=dict(text="<b>Faturamento Monetário (R$)</b>", font=dict(size=14)),
                tickprefix="R$ ",
                showgrid=True,
                gridcolor="#e9ecef",
                tickfont=dict(size=12),
                range=[0, max_fat * 1.35] if max_fat > 0 else None,
            ),
            yaxis2=dict(
                title=dict(text="<b>Devoluções (R$)</b>", font=dict(size=14)),
                overlaying="y",
                side="right",
                showgrid=False,
                tickfont=dict(size=12),
                range=[0, max_dev * 1.60] if max_dev > 0 else None,
            ),
            xaxis=dict(
                title=dict(text="<b>Data (Dia/Mês)</b>", font=dict(size=14)),
                type="category",
                tickfont=dict(size=12),
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.03,
                xanchor="right",
                x=1,
                font=dict(size=13),
            ),
        )

        st.plotly_chart(fig_fat_solo, use_container_width=True)

    st.divider()