import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from utils.loader import load_resumo_terceiros_MNOP
from utils.parser import fmt_brl


def render_secao_frete(df_filtrado: pd.DataFrame = None, col_fat_ativa: str = None, df_frete_bruto: pd.DataFrame = None):
    st.divider()
    st.markdown("### 🚚 Resumo do Custo de Frete Terceirizado por Transportadora")

    # Leitura dos dados das colunas M, N, O, P
    df_mnop = load_resumo_terceiros_MNOP()

    if df_mnop.empty:
        st.info("Tabela de frete por transportadora indisponível.")
        return

    # Separar corpo e Total Geral
    df_corpo = df_mnop[df_mnop["Transportadora"].astype(str).str.strip().str.upper() != "TOTAL GERAL"].copy()
    df_total = df_mnop[df_mnop["Transportadora"].astype(str).str.strip().str.upper() == "TOTAL GERAL"].copy()

    # Ordenar por maior valor de frete
    df_corpo = df_corpo.sort_values(by="Valor_Frete", ascending=False).reset_index(drop=True)
    df_exibicao = pd.concat([df_corpo, df_total], ignore_index=True)

    # Métricas de topo (Cards KPIs limpos sem menção a colunas)
    vlr_frete_acumulado = df_total["Valor_Frete"].sum() if not df_total.empty else df_corpo["Valor_Frete"].sum()
    vlr_nf_acumulado = df_total["Valor_NF"].sum() if not df_total.empty else df_corpo["Valor_NF"].sum()
    pct_media_geral = (vlr_frete_acumulado / vlr_nf_acumulado * 100) if vlr_nf_acumulado > 0 else 0.0

    k1, k2, k3 = st.columns(3)
    k1.metric("💵 Total Frete Acumulado", fmt_brl(vlr_frete_acumulado))
    k2.metric("📦 Total NF Atendida", fmt_brl(vlr_nf_acumulado))
    k3.metric("📊 % Frete Médio / NF", f"{pct_media_geral:.2f}%")

    st.markdown("---")

    # -------------------------------------------------------------
    # 🍕 1. GRÁFICO DE PIZZA - VALOR MONETÁRIO (R$)
    # -------------------------------------------------------------
    # 🍕 2. GRÁFICO DE PIZZA - PORCENTAGEM (%)
    # -------------------------------------------------------------
    col_piz1, col_piz2 = st.columns(2)

    with col_piz1:
        st.subheader("🍕 Distribuição por Valor Monetário (R$)")
        fig_pie_val = go.Figure(
            go.Pie(
                labels=df_corpo["Transportadora"],
                values=df_corpo["Valor_Frete"],
                hole=0.35,
                textinfo="label+value",
                hovertemplate="<b>%{label}</b><br>Frete: R$ %{value:,.2f}<br>Participação: %{percent}<extra></extra>",
                textfont=dict(size=11, color="#000000"),
                marker=dict(line=dict(color="#ffffff", width=2)),
            )
        )
        fig_pie_val.update_layout(
            template="plotly_white",
            height=480,
            margin=dict(l=20, r=20, t=30, b=20),
            showlegend=False,
        )
        st.plotly_chart(fig_pie_val, use_container_width=True)

    with col_piz2:
        st.subheader("🍕 Participação Percentual (%)")
        fig_pie_pct = go.Figure(
            go.Pie(
                labels=df_corpo["Transportadora"],
                values=df_corpo["Valor_Frete"],
                hole=0.35,
                textinfo="label+percent",
                hovertemplate="<b>%{label}</b><br>Participação: %{percent}<br>Frete: R$ %{value:,.2f}<extra></extra>",
                textfont=dict(size=11, color="#000000"),
                marker=dict(line=dict(color="#ffffff", width=2)),
            )
        )
        fig_pie_pct.update_layout(
            template="plotly_white",
            height=480,
            margin=dict(l=20, r=20, t=30, b=20),
            showlegend=False,
        )
        st.plotly_chart(fig_pie_pct, use_container_width=True)

    # -------------------------------------------------------------
    # 🏆 3. GRÁFICO TOP 10 TRANSPORTADORAS (VALOR E PORCENTAGEM)
    # -------------------------------------------------------------
    st.subheader("🏆 Top 10 Transportadoras: Valor de Frete (R$) & Porcentagem (%)")

    df_top10 = df_corpo.head(10).copy()
    eixo_x_top = df_top10["Transportadora"].tolist()
    y_frete_top = df_top10["Valor_Frete"].tolist()
    y_pct_top = (df_top10["Pct_Frete"] * 100).tolist()

    max_frete_top = max(y_frete_top) if y_frete_top else 1000.0
    max_pct_top = max(y_pct_top) if y_pct_top else 10.0

    fig_top10 = go.Figure()

    # Barras de Valor de Frete (R$)
    fig_top10.add_trace(
        go.Bar(
            x=eixo_x_top,
            y=y_frete_top,
            name="Valor Frete (R$)",
            marker=dict(color="#0077b6", line=dict(color="#000000", width=1.0)),
            text=[fmt_brl(v) for v in y_frete_top],
            textfont=dict(color="#000000", size=11, family="Arial"),
            textposition="outside",
            cliponaxis=False,
        )
    )

    # Linha com marcador de % Frete / NF
    fig_top10.add_trace(
        go.Scatter(
            x=eixo_x_top,
            y=y_pct_top,
            name="% Frete / NF",
            mode="lines+markers+text",
            marker=dict(color="#d97706", size=8, symbol="diamond"),
            line=dict(color="#d97706", width=2.5),
            text=[f"<b>{v:.2f}%</b>" for v in y_pct_top],
            textfont=dict(color="#000000", size=11, family="Arial"),
            textposition="top center",
            yaxis="y2",
        )
    )

    fig_top10.update_layout(
        template="plotly_white",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#000000", size=12, family="Arial"),
        margin=dict(l=50, r=50, t=60, b=80),
        height=520,
        bargap=0.20,
        yaxis=dict(
            title=dict(text="<b>Valor do Frete (R$)</b>", font=dict(size=13, color="#000000")),
            tickprefix="R$ ",
            showgrid=True,
            gridcolor="#e9ecef",
            range=[0, max_frete_top * 1.35],
        ),
        yaxis2=dict(
            title=dict(text="<b>% Frete / NF</b>", font=dict(size=13, color="#000000")),
            overlaying="y",
            side="right",
            showgrid=False,
            ticksuffix="%",
            range=[0, max_pct_top * 2.50],  # Espaço para não colidir rótulos
        ),
        xaxis=dict(type="category", tickangle=-25, tickfont=dict(size=11, color="#000000")),
        legend=dict(orientation="h", y=1.12, x=1, xanchor="right", font=dict(size=12, color="#000000")),
    )

    st.plotly_chart(fig_top10, use_container_width=True)

    # -------------------------------------------------------------
    # 📊 TABELA DE ACUMULADO GERAL (SEM MENÇÃO A COLUNAS)
    # -------------------------------------------------------------
    st.markdown("---")
    st.markdown("#### 📊 Acumulado Geral por Transportadora")

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