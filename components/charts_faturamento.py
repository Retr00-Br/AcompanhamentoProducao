import pandas as pd
import plotly.graph_objects as go
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
        fig_fat_solo = go.Figure()

        labels_fat = [fmt_brl(v) for v in df_filtrado[col_fat_ativa]]
        labels_dev = [fmt_brl(v) if v > 0 else "" for v in df_filtrado[col_dev_ativa]]

        max_fat = df_filtrado[col_fat_ativa].max() if not df_filtrado[col_fat_ativa].empty else 1000
        max_dev = df_filtrado[col_dev_ativa].max() if not df_filtrado[col_dev_ativa].empty else 1000

        # Barras de Faturamento (Texto no topo, sempre horizontal)
        fig_fat_solo.add_trace(
            go.Bar(
                x=df_filtrado["Data_Str"],
                y=df_filtrado[col_fat_ativa],
                name="Faturamento (R$)",
                marker=dict(color="#0077b6", line=dict(color="#000000", width=1.0)),
                text=labels_fat,
                textfont=dict(color="#000000", size=11),
                textposition="outside",
                textangle=0,  # Padronização horizontal
                cliponaxis=False,
            )
        )

        # Linha de Devoluções (Texto posicionado logo abaixo dos marcadores para evitar colisão)
        fig_fat_solo.add_trace(
            go.Scatter(
                x=df_filtrado["Data_Str"],
                y=df_filtrado[col_dev_ativa],
                name="Devoluções (R$)",
                mode="lines+markers+text",
                marker=dict(color="#d90429", size=7, symbol="circle"),
                line=dict(color="#d90429", width=2.0),
                text=labels_dev,
                textfont=dict(color="#d90429", size=11, family="Arial Black"),
                textposition="bottom center",
                textangle=0,  # Padronização horizontal
                yaxis="y2",
                cliponaxis=False,
            )
        )

        fig_fat_solo.update_layout(
            template="plotly_white",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#000000", size=13, family="Arial"),
            margin=dict(l=65, r=65, t=75, b=65),
            height=640,
            bargap=0.15,  # Aumenta a largura das barras
            yaxis=dict(
                title=dict(text="<b>Faturamento Monetário (R$)</b>", font=dict(size=14)),
                tickprefix="R$ ",
                showgrid=True,
                gridcolor="#e9ecef",
                tickfont=dict(size=12),
                # Range expandido para dar respiro aos números das barras
                range=[0, max_fat * 1.35] if max_fat > 0 else None,
            ),
            yaxis2=dict(
                title=dict(text="<b>Devoluções (R$)</b>", font=dict(size=14)),
                overlaying="y",
                side="right",
                showgrid=False,
                tickfont=dict(size=12),
                # Scale offset para afastar a linha dos topos de barras e evitar colisão
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