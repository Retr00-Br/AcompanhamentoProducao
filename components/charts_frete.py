import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from utils.parser import fmt_brl


def render_secao_frete(df_filtrado: pd.DataFrame, col_fat_ativa: str):
    st.divider()
    st.markdown("### 🚚 Indicadores & Análise de Frete Terceirizado")

    if df_filtrado.empty or "Total_Frete" not in df_filtrado.columns:
        st.info("Sem lançamentos de frete para o período selecionado.")
        return

    # Subconjunto estritamente contido no filtro de datas ativo do dashboard
    df_frete_ativo = df_filtrado.copy()

    fat_total = float(df_frete_ativo[col_fat_ativa].sum()) if col_fat_ativa in df_frete_ativo.columns else 0.0
    frete_total = float(df_frete_ativo["Total_Frete"].sum())

    df_dias_frete = df_frete_ativo[df_frete_ativo["Total_Frete"] > 0]
    dias_com_frete = len(df_dias_frete)
    divisor = dias_com_frete if dias_com_frete > 0 else 1
    media_frete_diaria = frete_total / divisor

    pct_frete_acumulado = (frete_total / fat_total * 100) if fat_total > 0 else 0.0

    # KPIs Numéricos
    k1, k2, k3, k4 = st.columns(4)
    k1.metric(
        "💵 Frete Total Acumulado",
        f"R$ {frete_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
    )
    k2.metric("📊 % Frete / Faturamento", f"{pct_frete_acumulado:.2f}%")
    k3.metric(
        "📈 Média Frete / Dia",
        f"R$ {media_frete_diaria:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
    )
    k4.metric("📅 Dias c/ Operação de Frete", f"{dias_com_frete} dias")

    if frete_total == 0:
        st.warning("⚠️ Não foram encontrados lançamentos de frete para as datas selecionadas neste filtro temporal.")
        return

    eixo_x = df_frete_ativo["Data_Str"].astype(str).tolist()
    y_fat = df_frete_ativo[col_fat_ativa].astype(float).tolist()
    y_frete = df_frete_ativo["Total_Frete"].astype(float).tolist()

    max_fat = max(y_fat) if y_fat else 1000.0
    max_frete = max(y_frete) if y_frete else 1000.0

    # -------------------------------------------------------------
    # GRÁFICO 1: FATURAMENTO VS FRETE POR DIA
    # -------------------------------------------------------------
    st.subheader("📊 Faturamento Diário vs. Valor do Frete Terceirizado")
    fig_fat_frete = go.Figure()

    fig_fat_frete.add_trace(
        go.Bar(
            x=eixo_x,
            y=y_fat,
            name="Faturamento (R$)",
            marker=dict(color="#0077b6", line=dict(color="#000000", width=1.0)),
            text=[fmt_brl(v) for v in y_fat],
            textfont=dict(color="#000000", size=11),
            textposition="outside",
            textangle=0,
            cliponaxis=False,
        )
    )

    fig_fat_frete.add_trace(
        go.Scatter(
            x=eixo_x,
            y=y_frete,
            name="Valor Frete (R$)",
            mode="lines+markers+text",
            marker=dict(color="#e76f51", size=7, symbol="diamond"),
            line=dict(color="#e76f51", width=2.5),
            text=[f"<b>R$ {v:,.0f}</b>" if v > 0 else "" for v in y_frete],
            textfont=dict(color="#e76f51", size=11),
            textposition="top center",
            yaxis="y2",
        )
    )

    fig_fat_frete.update_layout(
        template="plotly_white",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#000000", size=13, family="Arial"),
        margin=dict(l=65, r=65, t=65, b=65),
        height=580,
        bargap=0.15,
        yaxis=dict(
            title=dict(text="<b>Faturamento Monetário (R$)</b>", font=dict(size=14)),
            tickprefix="R$ ",
            showgrid=True,
            gridcolor="#e9ecef",
            range=[0, max_fat * 1.35] if max_fat > 0 else None,
        ),
        yaxis2=dict(
            title=dict(text="<b>Valor do Frete (R$)</b>", font=dict(size=14)),
            overlaying="y",
            side="right",
            showgrid=False,
            range=[0, max_frete * 1.50] if max_frete > 0 else None,
        ),
        xaxis=dict(type="category"),
        legend=dict(orientation="h", y=1.03, x=1, xanchor="right"),
    )

    st.plotly_chart(fig_fat_frete, use_container_width=True)

    # -------------------------------------------------------------
    # GRÁFICO 2: VALOR DE FRETE ISOLADO POR DIA (Respeitando a escala das datas ativas)
    # -------------------------------------------------------------
    st.subheader("📦 Custo Total de Frete por Dia (R$)")

    fig_frete_dia = go.Figure(
        go.Bar(
            x=eixo_x,
            y=y_frete,
            name="Frete Diário",
            marker=dict(color="#e76f51", line=dict(color="#000000", width=1.0)),
            text=[f"<b>R$ {v:,.0f}</b>" if v > 0 else "" for v in y_frete],
            textfont=dict(color="#000000", size=11),
            textposition="outside",
            textangle=0,
            cliponaxis=False,
        )
    )

    fig_frete_dia.update_layout(
        template="plotly_white",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#000000", size=13, family="Arial"),
        margin=dict(l=65, r=65, t=65, b=65),
        height=520,
        bargap=0.15,
        yaxis=dict(
            title=dict(text="<b>Valor de Frete (R$)</b>", font=dict(size=14)),
            tickprefix="R$ ",
            showgrid=True,
            gridcolor="#e9ecef",
            range=[0, max_frete * 1.30] if max_frete > 0 else None,
        ),
        xaxis=dict(type="category"),
    )

    st.plotly_chart(fig_frete_dia, use_container_width=True)