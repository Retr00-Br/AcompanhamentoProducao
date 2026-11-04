import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from utils.loader import load_resumo_terceiros_MNOP
from utils.parser import fmt_brl


def render_secao_frete(df_diario_completo: pd.DataFrame, col_fat_ativa: str, df_frete_bruto: pd.DataFrame = None):
    st.divider()
    st.markdown("### 🚚 Indicadores & Análise de Frete Terceirizado")

    if df_diario_completo is None or df_diario_completo.empty:
        st.info("Sem lançamentos de frete registrados.")
        return

    df_frete_base = df_diario_completo[df_diario_completo["Total_Frete"] > 0].copy()
    if df_frete_base.empty:
        df_frete_base = df_diario_completo.copy()

    st.markdown("#### 🗓️ Filtro Temporal Exclusivo da Seção de Fretes")
    c_cal1, c_cal2 = st.columns([2, 2])

    min_frete_date = df_frete_base["DATA"].min().date()
    max_frete_date = df_frete_base["DATA"].max().date()

    with c_cal1:
        datas_sel = st.date_input(
            "Selecione o Intervalo de Datas para Frete:",
            value=(min_frete_date, max_frete_date),
            min_value=df_diario_completo["DATA"].min().date(),
            max_value=df_diario_completo["DATA"].max().date(),
            key="filtro_calendario_fretes_exclusivo",
        )

    if isinstance(datas_sel, tuple) and len(datas_sel) == 2:
        dt_ini, dt_fim = datas_sel
    else:
        dt_ini, dt_fim = min_frete_date, max_frete_date

    df_frete_ativo = df_diario_completo[
        (df_diario_completo["DATA"].dt.date >= dt_ini) & (df_diario_completo["DATA"].dt.date <= dt_fim)
    ].copy().sort_values("DATA").reset_index(drop=True)

    df_frete_ativo["Data_Str"] = df_frete_ativo["DATA"].dt.strftime("%d/%m")

    col_fat = col_fat_ativa if col_fat_ativa in df_frete_ativo.columns else "Todas as Unidades (Geral)_Fat"
    fat_total = float(df_frete_ativo[col_fat].sum()) if col_fat in df_frete_ativo.columns else 0.0
    frete_total = float(df_frete_ativo["Total_Frete"].sum())

    pct_frete_sobre_faturamento = (frete_total / fat_total * 100) if fat_total > 0 else 0.0
    df_dias_frete = df_frete_ativo[df_frete_ativo["Total_Frete"] > 0]
    dias_com_frete = len(df_dias_frete)

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("💵 Total Frete Acumulado", fmt_brl(frete_total))
    k2.metric("📦 Faturamento Atendido no Período", fmt_brl(fat_total))
    k3.metric("🎯 % Frete / Faturamento Acumulado", f"{pct_frete_sobre_faturamento:.2f}%")
    k4.metric("📅 Dias c/ Operação de Frete", f"{dias_com_frete} dias")

    st.markdown("---")
    st.subheader("📈 Relação Diária: % do Custo de Frete sobre o Faturamento")

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

        # Barras de Faturamento com Hover Limpo
        fig_relacao.add_trace(
            go.Bar(
                x=eixo_x,
                y=y_fat,
                name="Faturamento (R$)",
                marker=dict(color="#0077b6", line=dict(color="#000000", width=1.0)),
                hovertemplate="<b>Data: %{x}</b><br>Faturamento: R$ %{y:,.2f}<extra></extra>",
            )
        )

        # Linha de % de Frete com marcadores de texto em destaque
        fig_relacao.add_trace(
            go.Scatter(
                x=eixo_x,
                y=y_pct_diario,
                name="% Frete / Faturamento",
                mode="lines+markers+text",
                marker=dict(color="#d97706", size=7, symbol="diamond"),
                line=dict(color="#d97706", width=2.2),
                text=[f"<b>{v:.1f}%</b>" if v > 0 else "" for v in y_pct_diario],
                textfont=dict(color="#000000", size=11, family="Arial"),
                textposition="top center",
                yaxis="y2",
                hovertemplate="<b>Data: %{x}</b><br>% Frete: %{y:.2f}%<extra></extra>",
            )
        )

        fig_relacao.update_layout(
            template="plotly_white",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#000000", size=12, family="Arial"),
            margin=dict(l=60, r=60, t=50, b=60),
            height=540,
            bargap=0.18,
            yaxis=dict(
                title=dict(text="<b>Faturamento Monetário (R$)</b>", font=dict(size=13, color="#000000")),
                tickprefix="R$ ",
                showgrid=True,
                gridcolor="#e9ecef",
                range=[0, max_fat * 1.20],
            ),
            yaxis2=dict(
                title=dict(text="<b>% Frete / Faturamento</b>", font=dict(size=13, color="#000000")),
                overlaying="y",
                side="right",
                showgrid=False,
                ticksuffix="%",
                range=[0, max(max_pct * 1.35, 10.0)],
            ),
            xaxis=dict(type="category", tickfont=dict(size=11, color="#000000")),
            legend=dict(orientation="h", y=1.12, x=1, xanchor="right", font=dict(size=12, color="#000000")),
        )

        st.plotly_chart(fig_relacao, use_container_width=True)

    # Pizzas e Acumulado por Transportadora
    df_mnop = load_resumo_terceiros_MNOP()
    if not df_mnop.empty:
        df_corpo = df_mnop[df_mnop["Transportadora"].astype(str).str.strip().str.upper() != "TOTAL GERAL"].copy()
        df_total = df_mnop[df_mnop["Transportadora"].astype(str).str.strip().str.upper() == "TOTAL GERAL"].copy()
        df_corpo = df_corpo.sort_values(by="Valor_Frete", ascending=False).reset_index(drop=True)

        st.markdown("---")
        col_piz1, col_piz2 = st.columns(2)

        total_frete_geral = df_corpo["Valor_Frete"].sum()
        df_pizza = df_corpo.copy()
        df_pizza["Pct_Geral"] = df_pizza["Valor_Frete"] / total_frete_geral if total_frete_geral > 0 else 0

        df_principais = df_pizza[df_pizza["Pct_Geral"] >= 0.02].copy()
        df_outros = df_pizza[df_pizza["Pct_Geral"] < 0.02]

        if not df_outros.empty:
            linha_outros = pd.DataFrame(
                [
                    {
                        "Transportadora": "OUTROS (< 2%)",
                        "Valor_NF": df_outros["Valor_NF"].sum(),
                        "Valor_Frete": df_outros["Valor_Frete"].sum(),
                        "Pct_Frete": (df_outros["Valor_Frete"].sum() / df_outros["Valor_NF"].sum())
                        if df_outros["Valor_NF"].sum() > 0
                        else 0.0,
                        "Pct_Geral": df_outros["Pct_Geral"].sum(),
                    }
                ]
            )
            df_pizza_final = pd.concat([df_principais, linha_outros], ignore_index=True)
        else:
            df_pizza_final = df_principais

        with col_piz1:
            st.subheader("🍕 Distribuição por Valor Monetário (R$)")
            fig_pie_val = go.Figure(
                go.Pie(
                    labels=df_pizza_final["Transportadora"],
                    values=df_pizza_final["Valor_Frete"],
                    hole=0.40,
                    textinfo="percent",
                    textposition="inside",
                    hovertemplate="<b>%{label}</b><br>Frete: R$ %{value:,.2f}<br>Participação: %{percent}<extra></extra>",
                    textfont=dict(size=12, color="#ffffff"),
                    marker=dict(line=dict(color="#ffffff", width=2)),
                )
            )
            fig_pie_val.update_layout(
                template="plotly_white",
                height=550,
                margin=dict(l=20, r=20, t=30, b=30),
                showlegend=True,
                legend=dict(orientation="v", y=0.5, x=1.02, font=dict(size=11, color="#000000")),
            )
            st.plotly_chart(fig_pie_val, use_container_width=True)

        with col_piz2:
            st.subheader("🍕 Participação Percentual no Total de Frete")
            fig_pie_pct = go.Figure(
                go.Pie(
                    labels=df_pizza_final["Transportadora"],
                    values=df_pizza_final["Valor_Frete"],
                    hole=0.40,
                    textinfo="label+percent",
                    textposition="inside",
                    hovertemplate="<b>%{label}</b><br>Participação: %{percent}<br>Frete: R$ %{value:,.2f}<extra></extra>",
                    textfont=dict(size=11, color="#ffffff"),
                    marker=dict(line=dict(color="#ffffff", width=2)),
                )
            )
            fig_pie_pct.update_layout(
                template="plotly_white",
                height=550,
                margin=dict(l=20, r=20, t=30, b=30),
                showlegend=True,
                legend=dict(orientation="v", y=0.5, x=1.02, font=dict(size=11, color="#000000")),
            )
            st.plotly_chart(fig_pie_pct, use_container_width=True)

        st.subheader("🏆 Top 10 Transportadoras: Valor de Frete (R$) & Porcentagem (%)")
        df_top10 = df_corpo.head(10).copy()
        eixo_x_top = df_top10["Transportadora"].tolist()
        y_frete_top = df_top10["Valor_Frete"].tolist()
        y_pct_top = (df_top10["Pct_Frete"] * 100).tolist()

        max_frete_top = max(y_frete_top) if y_frete_top else 1000.0
        max_pct_top = max(y_pct_top) if y_pct_top else 10.0

        fig_top10 = go.Figure()
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
                range=[0, max_pct_top * 2.50],
            ),
            xaxis=dict(type="category", tickangle=-25, tickfont=dict(size=11, color="#000000")),
            legend=dict(orientation="h", y=1.12, x=1, xanchor="right", font=dict(size=12, color="#000000")),
        )

        st.plotly_chart(fig_top10, use_container_width=True)

        st.markdown("---")
        st.markdown("#### 📊 Acumulado Geral por Transportadora")
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
        def fmt_executivo_brl(val: float) -> str:
    """Retorna o valor monetário abreviado para rótulos de gráfico (ex: R$ 457k, R$ 1,5M)."""
    try:
        if pd.isna(val) or val <= 0:
            return ""
        val = float(val)
        if val >= 1_000_000:
            return f"R$ {val / 1_000_000:.1f}M".replace(".", ",")
        elif val >= 1_000:
            return f"R$ {val / 1_000:.0f}k"
        else:
            return f"R$ {val:.0f}"
    except Exception:
        return ""


# Dentro da função render_secao_frete, no grafico fig_relacao:
        fig_relacao.add_trace(
            go.Bar(
                x=eixo_x,
                y=y_fat,
                name="Faturamento (R$)",
                marker=dict(color="#0077b6", line=dict(color="#000000", width=1.0)),
                text=[fmt_executivo_brl(v) for v in y_fat],
                textfont=dict(color="#000000", size=10, family="Arial Black"),
                textangle=-90,
                textposition="outside",
                cliponaxis=False,
                hovertemplate="<b>Data: %{x}</b><br>Faturamento: R$ %{y:,.2f}<extra></extra>",
            )
        )