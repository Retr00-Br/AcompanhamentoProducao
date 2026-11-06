import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from utils.loader import load_resumo_terceiros_MNOP


def render_secao_frete(df_diario: pd.DataFrame, col_fat_ativa: str, df_frete_tratado: pd.DataFrame):
    st.markdown("---")
    st.markdown("### 🚚 Gestão & Performance de Frete Terceirizado")

    if df_frete_tratado is None or df_frete_tratado.empty:
        st.info("Sem dados de frete terceirizado disponíveis.")
        return

    col_fat_geral = "Todas as Unidades (Geral)_Fat" if "Todas as Unidades (Geral)_Fat" in df_diario.columns else col_fat_ativa

    # =========================================================================
    # 1. COMPARATIVO MENSAL FRETE VS FATURAMENTO (KPIs ISOLADOS NO TOPO)
    # =========================================================================
    st.markdown("### 📊 Comparativo Mensal: Custo de Frete vs. Faturamento Monetário")

    df_diario_temp = df_diario.copy()
    df_diario_temp["Mes_Ano"] = df_diario_temp["DATA"].dt.strftime("%Y-%m")
    fat_mensal = df_diario_temp.groupby("Mes_Ano")[col_fat_geral].sum().reset_index(name="Faturamento")

    df_frete_temp = df_frete_tratado.copy()
    df_frete_temp["Mes_Ano"] = df_frete_temp["DATA"].dt.strftime("%Y-%m")
    frete_mensal = df_frete_temp.groupby("Mes_Ano")["Valor Total Frete"].sum().reset_index(name="Frete")

    df_comp_mensal = pd.merge(fat_mensal, frete_mensal, on="Mes_Ano", how="outer").fillna(0.0)
    df_comp_mensal = df_comp_mensal.sort_values("Mes_Ano").reset_index(drop=True)

    df_comp_mensal["Pct_Frete"] = (df_comp_mensal["Frete"] / df_comp_mensal["Faturamento"]) * 100
    df_comp_mensal["Pct_Frete"] = df_comp_mensal["Pct_Frete"].fillna(0.0)

    eixo_x_mes = df_comp_mensal["Mes_Ano"].tolist()
    y_fat = df_comp_mensal["Faturamento"].tolist()
    y_frete = df_comp_mensal["Frete"].tolist()
    pct_labels = df_comp_mensal["Pct_Frete"].tolist()

    max_val_comp = max(max(y_fat, default=100), max(y_frete, default=100))

    fig_comp = go.Figure()

    # Barra 1: Faturamento Monetário Total
    fig_comp.add_trace(
        go.Bar(
            x=eixo_x_mes,
            y=y_fat,
            name="Faturamento Total (R$)",
            marker=dict(color="#1f77b4", line=dict(color="#000000", width=1.0)),
            text=[f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") for v in y_fat],
            textposition="outside",
            textfont=dict(size=11, color="#000000"),
            cliponaxis=False,
            hovertemplate="<b>Mês: %{x}</b><br>Faturamento: R$ %{y:,.2f}<extra></extra>",
        )
    )

    # Barra 2: Custo de Frete Terceirizado
    fig_comp.add_trace(
        go.Bar(
            x=eixo_x_mes,
            y=y_frete,
            name="Custo de Frete (R$)",
            marker=dict(color="#d62728", line=dict(color="#000000", width=1.0)),
            text=[f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") for v in y_frete],
            textposition="outside",
            textfont=dict(size=11, color="#000000"),
            cliponaxis=False,
            hovertemplate="<b>Mês: %{x}</b><br>Frete: R$ %{y:,.2f}<extra></extra>",
        )
    )

    # PORCENTAGENS ISOLADAS NO TOPO ABSOLUTO (Y FIXO ACIMA DA MAIOR BARRA)
    y_topo_absoluto = max_val_comp * 1.25

    for mes, p_val in zip(eixo_x_mes, pct_labels):
        fig_comp.add_annotation(
            x=mes,
            y=y_topo_absoluto,
            text=f"<b>% Frete / Fat: {p_val:.2f}%</b>",
            showarrow=False,
            font=dict(size=12, color="#d62728", family="Arial Black"),
            bgcolor="#f8d7da",
            bordercolor="#f5c6cb",
            borderwidth=1,
            borderpad=6,
        )

    fig_comp.update_layout(
        template="plotly_white",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#000000", size=12, family="Arial"),
        margin=dict(l=50, r=50, t=70, b=50),
        height=540,
        barmode="group",
        bargap=0.25,
        yaxis=dict(
            title=dict(text="<b>Valor Monetário (R$)</b>", font=dict(size=13, color="#000000")),
            showgrid=True,
            gridcolor="#e9ecef",
            range=[0, max_val_comp * 1.40],
        ),
        xaxis=dict(type="category", tickfont=dict(size=11, color="#000000")),
        legend=dict(orientation="h", y=1.14, x=1, xanchor="right", font=dict(size=12, color="#000000")),
    )

    st.plotly_chart(fig_comp, use_container_width=True)

    # =========================================================================
    # 2. CALENDÁRIO ISOLADO + KPIS E GRÁFICO DIÁRIO
    # =========================================================================
    st.markdown("---")
    st.markdown("### 📈 Relação Diária: % do Custo de Frete sobre o Faturamento")

    df_diario_frete_base = pd.merge(
        df_diario[["DATA", col_fat_geral]],
        df_frete_tratado.groupby("DATA")["Valor Total Frete"].sum().reset_index(),
        on="DATA",
        how="inner",
    ).sort_values("DATA").reset_index(drop=True)

    min_d_frete = df_diario_frete_base["DATA"].min().date()
    max_d_frete = df_diario_frete_base["DATA"].max().date()

    # 📅 CALENDÁRIO EXCLUSIVO (APENAS ALTERA ESSE GRÁFICO E SEUS KPIS)
    col_cal1, col_cal2 = st.columns([2, 3])
    with col_cal1:
        sel_datas_frete = st.date_input(
            "📅 Selecione o Intervalo de Datas exclusivo para o Frete Diário:",
            value=(min_d_frete, max_d_frete),
            min_value=min_d_frete,
            max_value=max_d_frete,
            key="calendario_exclusivo_frete_diario",
        )

    if isinstance(sel_datas_frete, tuple) and len(sel_datas_frete) == 2:
        dt_start, dt_end = sel_datas_frete
    else:
        dt_start, dt_end = min_d_frete, max_d_frete

    df_diario_frete = df_diario_frete_base[
        (df_diario_frete_base["DATA"].dt.date >= dt_start) & (df_diario_frete_base["DATA"].dt.date <= dt_end)
    ].copy().reset_index(drop=True)

    # 🎯 KPIS ATUALIZADOS PELO CALENDÁRIO EXCLUSIVO
    total_frete_sel = df_diario_frete["Valor Total Frete"].sum()
    total_fat_sel = df_diario_frete[col_fat_geral].sum()
    pct_frete_sel = (total_frete_sel / total_fat_sel * 100) if total_fat_sel > 0 else 0.0
    dias_frete_sel = df_diario_frete["DATA"].nunique()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💵 Total Frete Acumulado", f"R$ {total_frete_sel:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    c2.metric("📦 Faturamento Atendido", f"R$ {total_fat_sel:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    c3.metric("🎯 % Frete / Faturamento", f"{pct_frete_sel:.2f}%")
    c4.metric("📅 Dias c/ Operação Frete", f"{dias_frete_sel} dias")

    if df_diario_frete.empty:
        st.info("Sem lançamentos de frete no período selecionado no calendário.")
        return

    df_diario_frete["Data_Str"] = df_diario_frete["DATA"].dt.strftime("%d/%m")
    df_diario_frete["Pct_Frete_Dia"] = (df_diario_frete["Valor Total Frete"] / df_diario_frete[col_fat_geral] * 100).fillna(0.0)

    def fmt_val_completo(v):
        if v > 0:
            return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return ""

    labels_barras = [fmt_val_completo(v) for v in df_diario_frete[col_fat_geral]]

    fig_diario = go.Figure()

    # Colunas Azuis de Faturamento
    fig_diario.add_trace(
        go.Bar(
            x=df_diario_frete["Data_Str"],
            y=df_diario_frete[col_fat_geral],
            name="Faturamento (R$)",
            marker=dict(color="#2b5c8f", line=dict(color="#000000", width=0.5)),
            text=labels_barras,
            textposition="outside",
            textfont=dict(size=10, color="#000000", family="Arial Black"),
            cliponaxis=False,
            yaxis="y1",
            hovertemplate="<b>Data: %{x}</b><br>Faturamento: R$ %{y:,.2f}<extra></extra>",
        )
    )

    # Linha Laranja de Porcentagem isolada no topo via eixo Y2 isolado
    fig_diario.add_trace(
        go.Scatter(
            x=df_diario_frete["Data_Str"],
            y=df_diario_frete["Pct_Frete_Dia"],
            name="% Frete / Faturamento",
            mode="lines+markers+text",
            text=[f"<b>{v:.1f}%</b>" if v > 0 else "" for v in df_diario_frete["Pct_Frete_Dia"]],
            textposition="top center",
            textfont=dict(size=10, color="#d97706", family="Arial Black"),
            line=dict(color="#d97706", width=2.5),
            marker=dict(size=6, color="#d97706"),
            yaxis="y2",
            hovertemplate="<b>Data: %{x}</b><br>% Frete: %{y:.2f}%<extra></extra>",
        )
    )

    max_fat = df_diario_frete[col_fat_geral].max()
    max_pct = df_diario_frete["Pct_Frete_Dia"].max()

    fig_diario.update_layout(
        template="plotly_white",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#000000", size=12),
        margin=dict(l=50, r=50, t=60, b=50),
        height=540,
        yaxis=dict(
            title=dict(text="<b>Faturamento Monetário (R$)</b>", font=dict(color="#000000")),
            showgrid=True,
            gridcolor="#e9ecef",
            range=[0, max_fat * 1.35],
        ),
        yaxis2=dict(
            title=dict(text="<b>% Frete / Faturamento</b>", font=dict(color="#d97706")),
            overlaying="y",
            side="right",
            showgrid=False,
            ticksuffix="%",
            range=[0, max(max_pct * 1.45, 45.0)],  # Isola a linha no topo absoluto
        ),
        legend=dict(orientation="h", y=1.14, x=1, xanchor="right"),
    )

    st.plotly_chart(fig_diario, use_container_width=True)

    # =========================================================================
    # 3. GRÁFICOS DE PIZZA & TABELA DE TERCEIROS MNOP
    # =========================================================================
    df_mnop = load_resumo_terceiros_MNOP()

    if df_mnop is not None and not df_mnop.empty:
        st.markdown("---")
        st.markdown("### 🍕 Distribuição por Transportadora Terceirizada (Resumo MNOP)")

        df_mnop_clean = df_mnop[~df_mnop["Transportadora"].astype(str).str.upper().str.contains("TOTAL")].copy()
        df_mnop_clean = df_mnop_clean.sort_values(by="Valor_Frete", ascending=False).reset_index(drop=True)

        col_p1, col_p2 = st.columns(2)

        with col_p1:
            fig_p1 = go.Figure(
                go.Pie(
                    labels=df_mnop_clean["Transportadora"],
                    values=df_mnop_clean["Valor_Frete"],
                    hole=0.45,
                    textinfo="percent",
                    textposition="inside",
                    hoverinfo="label+value+percent",
                    textfont=dict(size=11),
                    hovertemplate="<b>%{label}</b><br>Frete: R$ %{value:,.2f}<br>Participação: %{percent}<extra></extra>",
                )
            )
            fig_p1.update_layout(
                title=dict(text="<b>Participação no Custo Total de Frete</b>", font=dict(size=14, color="#000000")),
                template="plotly_white",
                height=460,
                margin=dict(l=20, r=20, t=50, b=20),
                showlegend=True,
                legend=dict(orientation="v", y=0.5, x=1.02),
            )
            st.plotly_chart(fig_p1, use_container_width=True)

        with col_p2:
            fig_p2 = go.Figure(
                go.Pie(
                    labels=df_mnop_clean["Transportadora"],
                    values=df_mnop_clean["Valor_NF"],
                    hole=0.45,
                    textinfo="percent",
                    textposition="inside",
                    hoverinfo="label+value+percent",
                    textfont=dict(size=11),
                    hovertemplate="<b>%{label}</b><br>Valor NF: R$ %{value:,.2f}<br>Participação: %{percent}<extra></extra>",
                )
            )
            fig_p2.update_layout(
                title=dict(text="<b>Participação no Faturamento Atendido (NFs)</b>", font=dict(size=14, color="#000000")),
                template="plotly_white",
                height=460,
                margin=dict(l=20, r=20, t=50, b=20),
                showlegend=True,
                legend=dict(orientation="v", y=0.5, x=1.02),
            )
            st.plotly_chart(fig_p2, use_container_width=True)

        # TABELA DE GASTOS COM TERCEIROS MNOP
        st.markdown("---")
        st.markdown("### 📋 Tabela Resumo: Gastos por Transportadora Terceirizada (MNOP)")

        df_tabela_mnop = df_mnop_clean.copy()
        df_tabela_mnop["Valor_NF_Str"] = df_tabela_mnop["Valor_NF"].apply(lambda v: f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        df_tabela_mnop["Valor_Frete_Str"] = df_tabela_mnop["Valor_Frete"].apply(lambda v: f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        df_tabela_mnop["Pct_Frete_Str"] = df_tabela_mnop["Pct_Frete"].apply(lambda v: f"{v*100:.2f}%" if v <= 1.0 else f"{v:.2f}%")

        df_tabela_final = df_tabela_mnop[["Transportadora", "Valor_NF_Str", "Valor_Frete_Str", "Pct_Frete_Str"]].rename(
            columns={
                "Valor_NF_Str": "Faturamento Atendido (NFs)",
                "Valor_Frete_Str": "Valor Total Frete (R$)",
                "Pct_Frete_Str": "% Custo Frete / NF",
            }
        )

        st.dataframe(df_tabela_final, use_container_width=True)