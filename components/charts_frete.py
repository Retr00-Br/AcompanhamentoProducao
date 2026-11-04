import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from utils.loader import load_resumo_terceiros_MNOP
from utils.parser import fmt_brl


def render_secao_frete(df_filtrado: pd.DataFrame, col_fat_ativa: str, df_frete_bruto: pd.DataFrame = None):
    st.divider()
    st.markdown("### 🚚 Indicadores & Análise de Frete Terceirizado")

    if df_filtrado.empty:
        st.info("Sem lançamentos de frete para o período selecionado.")
        return

    df_frete_ativo = df_filtrado.copy()

    col_fat = col_fat_ativa if col_fat_ativa in df_frete_ativo.columns else "Todas as Unidades (Geral)_Fat"
    fat_total = float(df_frete_ativo[col_fat].sum()) if col_fat in df_frete_ativo.columns else 0.0
    frete_total = float(df_frete_ativo["Total_Frete"].sum())

    pct_frete_sobre_faturamento = (frete_total / fat_total * 100) if fat_total > 0 else 0.0

    df_dias_frete = df_frete_ativo[df_frete_ativo["Total_Frete"] > 0]
    dias_com_frete = len(df_dias_frete)
    media_frete_diaria = frete_total / (dias_com_frete if dias_com_frete > 0 else 1)

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("💵 Total Frete no Período", fmt_brl(frete_total))
    k2.metric("📦 Faturamento Atendido no Período", fmt_brl(fat_total))
    k3.metric("🎯 % Frete / Faturamento Acumulado", f"{pct_frete_sobre_faturamento:.2f}%")
    k4.metric("📅 Dias c/ Operação de Frete", f"{dias_com_frete} dias")

    st.markdown("---")

    # Gráfico Diário de Relação % Frete por Dia x Faturamento R$
    st.subheader("📈 Relação Diária: % do Custo de Frete sobre o Faturamento (Coluna H x Coluna C)")

    df_chart = df_frete_ativo[(df_frete_ativo["Total_Frete"] > 0) | (df_frete_ativo[col_fat] > 0)].copy()

    if not df_chart.empty:
        eixo_x = df_chart["Data_Str"].astype(str).tolist()
        y_fat = df_chart[col_fat].astype(float).tolist()
        y_frete = df_chart["Total_Frete"].astype(float).tolist()

        y_pct_diario = [
            (frete / fat * 100) if fat > 0 else 0.0
            for frete, fat in zip(y_frete, y_fat)
        ]

        max_fat = max(y_fat) if y_fat else 1000.0
        max_pct = max(y_pct_diario) if y_pct_diario else 10.0

        fig_relacao = go.Figure()

        fig_relacao.add_trace(
            go.Bar(
                x=eixo_x,
                y=y_fat,
                name="Faturamento (R$)",
                marker=dict(color="#0077b6", line=dict(color="#000000", width=1.0)),
                text=[fmt_brl(v) if v > 0 else "" for v in y_fat],
                textfont=dict(color="#000000", size=10, family="Arial"),
                textposition="outside",
                cliponaxis=False,
            )
        )

        fig_relacao.add_trace(
            go.Scatter(
                x=eixo_x,
                y=y_pct_diario,
                name="% Frete / Faturamento",
                mode="lines+markers+text",
                marker=dict(color="#d97706", size=8, symbol="diamond"),
                line=dict(color="#d97706", width=2.5),
                text=[f"<b>{v:.1f}%</b>" if v > 0 else "" for v in y_pct_diario],
                textfont=dict(color="#000000", size=10, family="Arial"),
                textposition="top center",
                yaxis="y2",
            )
        )

        fig_relacao.update_layout(
            template="plotly_white",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#000000", size=12, family="Arial"),
            margin=dict(l=60, r=60, t=60, b=60),
            height=540,
            bargap=0.18,
            yaxis=dict(
                title=dict(text="<b>Faturamento Monetário (R$)</b>", font=dict(size=13, color="#000000")),
                tickprefix="R$ ",
                showgrid=True,
                gridcolor="#e9ecef",
                range=[0, max_fat * 1.35],
            ),
            yaxis2=dict(
                title=dict(text="<b>% Frete / Faturamento</b>", font=dict(size=13, color="#000000")),
                overlaying="y",
                side="right",
                showgrid=False,
                ticksuffix="%",
                range=[0, max_pct * 2.50],
            ),
            xaxis=dict(type="category", tickfont=dict(size=11, color="#000000")),
            legend=dict(orientation="h", y=1.10, x=1, xanchor="right", font=dict(size=12, color="#000000")),
        )

        st.plotly_chart(fig_relacao, use_container_width=True)

    # Tabela de Acumulado por Transportadora (Colunas M, N, O e P)
    st.markdown("---")
    st.markdown("#### 📊 Acumulado Geral por Transportadora")

    df_mnop = load_resumo_terceiros_MNOP()
    if not df_mnop.empty:
        df_corpo = df_mnop[df_mnop["Transportadora"].astype(str).str.strip().str.upper() != "TOTAL GERAL"].copy()
        df_total = df_mnop[df_mnop["Transportadora"].astype(str).str.strip().str.upper() == "TOTAL GERAL"].copy()

        df_corpo = df_corpo.sort_values(by="Valor_Frete", ascending=False).reset_index(drop=True)
        df_exibicao = pd.concat([df_corpo, df_total], ignore_index=True)

        df_formatado = df_exibicao.copy()
        df_formatado["Valor NF (R$)"] = df_formatado["Valor_NF"].apply(fmt_brl)
        df_formatado["Valor Frete (R$)"] = df_formatado["Valor_Frete"].apply(fmt_brl)
        df_formatado["% Frete / NF"] = (df_formatado["Pct_Frete"] * 100).map("{:.2f}%".format)

        df_final = df_formatado[["Transportadora", "Valor NF (R$)", "Valor Frete (R$)", "% Frete / NF"]]

        st.dataframe(
            df_final,
            use_container_width=True,
            hide_index=True,
            height=min(600, len(df_final) * 38 + 40),
        )