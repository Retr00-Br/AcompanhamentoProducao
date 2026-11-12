import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from utils.loader import load_resumo_terceiros_MNOP


def render_secao_frete(df_diario: pd.DataFrame, col_fat_ativa: str, df_frete_tratado: pd.DataFrame):
    st.markdown("### 🚚 Gestão & Performance de Frete Terceirizado")

    if df_frete_tratado is None or df_frete_tratado.empty:
        st.info("Sem dados de frete terceirizado disponíveis.")
        return

    col_fat_geral = "Todas as Unidades (Geral)_Fat" if "Todas as Unidades (Geral)_Fat" in df_diario.columns else col_fat_ativa

    df_d = df_diario.copy()
    df_d["DATA"] = pd.to_datetime(df_d["DATA"]).dt.normalize()

    df_f = df_frete_tratado.copy()
    df_f["DATA"] = pd.to_datetime(df_f["DATA"]).dt.normalize()

    # =========================================================================
    # 1. COMPARATIVO MENSAL FRETE VS FATURAMENTO MONETÁRIO (INALTERADO)
    # =========================================================================
    st.markdown("### 📊 Comparativo Mensal: Custo de Frete vs. Faturamento Monetário")

    df_d["Mes_Ano"] = df_d["DATA"].dt.strftime("%Y-%m")
    fat_mensal = df_d.groupby("Mes_Ano")[col_fat_geral].sum().reset_index(name="Faturamento")

    df_f["Mes_Ano"] = df_f["DATA"].dt.strftime("%Y-%m")
    frete_mensal = df_f.groupby("Mes_Ano")["Valor Total Frete"].sum().reset_index(name="Frete")

    df_comp_mensal = pd.merge(fat_mensal, frete_mensal, on="Mes_Ano", how="outer").fillna(0.0)
    df_comp_mensal = df_comp_mensal.sort_values("Mes_Ano").reset_index(drop=True)

    df_comp_mensal["Pct_Frete"] = (df_comp_mensal["Frete"] / df_comp_mensal["Faturamento"].replace(0, pd.NA)) * 100
    df_comp_mensal["Pct_Frete"] = df_comp_mensal["Pct_Frete"].fillna(0.0)

    eixo_x_mes = df_comp_mensal["Mes_Ano"].tolist()
    y_fat = df_comp_mensal["Faturamento"].tolist()
    y_frete = df_comp_mensal["Frete"].tolist()
    pct_labels = df_comp_mensal["Pct_Frete"].tolist()

    max_val_comp = max(max(y_fat, default=100), max(y_frete, default=100))

    fig_comp = go.Figure()

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
    # 2. FILTRO TEMPORAL COMPLETO + GRÁFICO DIÁRIO LADO A LADO
    # =========================================================================
    st.markdown("---")
    st.markdown("### 📈 Relação Diária: % do Custo de Frete sobre o Faturamento")

    frete_diario_agg = df_f.groupby("DATA")["Valor Total Frete"].sum().reset_index()

    df_diario_frete_base = pd.merge(
        frete_diario_agg,
        df_d[["DATA", col_fat_geral]],
        on="DATA",
        how="left",
    ).fillna({col_fat_geral: 0.0}).sort_values("DATA").reset_index(drop=True)

    if df_diario_frete_base.empty:
        st.info("Sem lançamentos de frete registrados.")
        return

    col_f1, col_f2 = st.columns([1.5, 3])

    with col_f1:
        tipo_filtro_frete = st.radio(
            "Filtrar período do Frete por:",
            ["Intervalo de Calendário", "Por Mês", "Por Semana do Ano"],
            horizontal=True,
            key="filtro_frete_radio",
        )

    min_date_f = df_diario_frete_base["DATA"].min().date()
    max_date_f = df_diario_frete_base["DATA"].max().date()

    with col_f2:
        if tipo_filtro_frete == "Intervalo de Calendário":
            datas_frete_sel = st.date_input(
                "Selecione o Período exclusivo para o Frete:",
                value=(min_date_f, max_date_f),
                min_value=min_date_f,
                max_value=max_date_f,
                key="filtro_frete_dates",
            )
            dt_inicio_f, dt_fim_f = (
                datas_frete_sel if isinstance(datas_frete_sel, tuple) and len(datas_frete_sel) == 2 else (min_date_f, max_date_f)
            )

        elif tipo_filtro_frete == "Por Mês":
            df_diario_frete_base["Mes_Ano"] = df_diario_frete_base["DATA"].dt.strftime("%Y-%m")
            meses_f = sorted(df_diario_frete_base["Mes_Ano"].unique().tolist())
            mes_sel_f = st.selectbox("Selecione o Mês:", meses_f, index=len(meses_f) - 1, key="filtro_frete_mes")
            dt_inicio_f = df_diario_frete_base[df_diario_frete_base["Mes_Ano"] == mes_sel_f]["DATA"].min().date()
            dt_fim_f = df_diario_frete_base[df_diario_frete_base["Mes_Ano"] == mes_sel_f]["DATA"].max().date()

        else:
            df_diario_frete_base["Semana_Inicio"] = df_diario_frete_base["DATA"].apply(lambda d: d - pd.Timedelta(days=d.weekday()))
            df_diario_frete_base["Semana_Fim"] = df_diario_frete_base["Semana_Inicio"] + pd.Timedelta(days=6)

            df_diario_frete_base["Semana_Label"] = (
                "Semana do dia "
                + df_diario_frete_base["Semana_Inicio"].dt.strftime("%d/%m")
                + " - "
                + df_diario_frete_base["Semana_Fim"].dt.strftime("%d/%m")
            )

            df_sem_f_ord = df_diario_frete_base.sort_values("Semana_Inicio")
            semanas_f = df_sem_f_ord["Semana_Label"].unique().tolist()

            semana_sel_f = st.selectbox(
                "Selecione a Semana:",
                semanas_f,
                index=len(semanas_f) - 1,
                key="filtro_frete_semana",
            )

            dt_inicio_f = df_diario_frete_base[df_diario_frete_base["Semana_Label"] == semana_sel_f]["DATA"].min().date()
            dt_fim_f = df_diario_frete_base[df_diario_frete_base["Semana_Label"] == semana_sel_f]["DATA"].max().date()

    df_diario_frete = df_diario_frete_base[
        (df_diario_frete_base["DATA"].dt.date >= dt_inicio_f) & (df_diario_frete_base["DATA"].dt.date <= dt_fim_f)
    ].copy().reset_index(drop=True)

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
        st.info("Sem lançamentos no período selecionado.")
        return

    df_diario_frete["Data_Str"] = df_diario_frete["DATA"].dt.strftime("%d/%m")
    df_diario_frete["Pct_Frete_Dia"] = (
        df_diario_frete["Valor Total Frete"] / df_diario_frete[col_fat_geral].replace(0, pd.NA) * 100
    ).fillna(0.0)

    def fmt_val_exato(v):
        if v > 0:
            return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return ""

    labels_fat = [fmt_val_exato(v) for v in df_diario_frete[col_fat_geral]]
    labels_pct = [f"{v:.2f}%" if v > 0 else "" for v in df_diario_frete["Pct_Frete_Dia"]]

    fig_diario = go.Figure()

    fig_diario.add_trace(
        go.Bar(
            x=df_diario_frete["Data_Str"],
            y=df_diario_frete[col_fat_geral],
            name="Faturamento (R$)",
            marker=dict(color="#1f77b4", line=dict(color="#000000", width=0.8)),
            text=labels_fat,
            textposition="outside",
            textfont=dict(size=10, color="#000000", family="Arial Black"),
            cliponaxis=False,
            offsetgroup=1,
            yaxis="y1",
            hovertemplate="<b>Data: %{x}</b><br>Faturamento: R$ %{y:,.2f}<extra></extra>",
        )
    )

    fig_diario.add_trace(
        go.Bar(
            x=df_diario_frete["Data_Str"],
            y=df_diario_frete["Pct_Frete_Dia"],
            name="% Frete / Faturamento",
            marker=dict(color="#d97706", line=dict(color="#000000", width=0.8)),
            text=labels_pct,
            textposition="outside",
            textfont=dict(size=10, color="#d97706", family="Arial Black"),
            cliponaxis=False,
            offsetgroup=2,
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
        font=dict(color="#000000", size=12, family="Arial"),
        margin=dict(l=50, r=50, t=60, b=60),
        height=540,
        barmode="group",
        bargap=0.15,
        bargroupgap=0.03,
        yaxis=dict(
            title=dict(text="<b>Faturamento Monetário (R$)</b>", font=dict(color="#000000", size=13)),
            showgrid=True,
            gridcolor="#e9ecef",
            range=[0, max(max_fat * 1.35, 100.0)],
        ),
        yaxis2=dict(
            title=dict(text="<b>% Frete / Faturamento</b>", font=dict(color="#d97706", size=13)),
            overlaying="y",
            side="right",
            showgrid=False,
            ticksuffix="%",
            range=[0, max(max_pct * 1.35, 40.0)],
        ),
        xaxis=dict(type="category", tickfont=dict(size=11, color="#000000")),
        legend=dict(orientation="h", y=1.14, x=1, xanchor="right", font=dict(size=12, color="#000000")),
    )

    st.plotly_chart(fig_diario, use_container_width=True)

    # =========================================================================
    # 3. PIZZAS E TABELA TERCEIROS (ÚLTIMA TABELA DE CADA ABA: RÓTULOS DE LINHA | VLR NF | VL FRETE | %)
    # =========================================================================
    df_mnop_clean = load_resumo_terceiros_MNOP()

    if df_mnop_clean is not None and not df_mnop_clean.empty:
        st.markdown("---")
        st.markdown("### 🍕 Distribuição por Transportadora Terceirizada (Consolidado Abas 08-09 & 10)")

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

        st.markdown("---")
        st.markdown("### 📋 Tabela Resumo: Gastos por Transportadora Terceirizada (Colunas A-U)")

        df_tabela_mnop = df_mnop_clean.copy()
        df_tabela_mnop["Valor_NF_Str"] = df_tabela_mnop["Valor_NF"].apply(
            lambda v: f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )
        df_tabela_mnop["Valor_Frete_Str"] = df_tabela_mnop["Valor_Frete"].apply(
            lambda v: f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )
        df_tabela_mnop["Pct_Frete_Str"] = df_tabela_mnop["Pct_Frete"].apply(lambda v: f"{v*100:.2f}%")

        df_tabela_final = df_tabela_mnop[["Transportadora", "Valor_NF_Str", "Valor_Frete_Str", "Pct_Frete_Str"]].rename(
            columns={
                "Valor_NF_Str": "Faturamento Atendido (NFs)",
                "Valor_Frete_Str": "Valor Total Frete (R$)",
                "Pct_Frete_Str": "% Custo Frete / NF",
            }
        )

        st.dataframe(df_tabela_final, use_container_width=True)

        # =====================================================================
        # 4. NOVO KPI & GRÁFICO: VALOR TOTAL NFs X FRETE X % POR TRANSPORTADORA
        # (Exatamente igual ao modelo do gráfico "Comparativo Mensal: Custo de Frete vs. Faturamento Monetário")
        # =====================================================================
        st.markdown("---")
        st.markdown("### 📊 Comparativo por Transportadora: Valor Total das NFs vs. Custo de Frete (% Frete / NF)")

        total_nf_transp = df_mnop_clean["Valor_NF"].sum()
        total_fr_transp = df_mnop_clean["Valor_Frete"].sum()
        pct_medio_transp = (total_fr_transp / total_nf_transp * 100) if total_nf_transp > 0 else 0.0
        top_transp_nome = df_mnop_clean.iloc[0]["Transportadora"]
        top_transp_val = df_mnop_clean.iloc[0]["Valor_Frete"]

        kt1, kt2, kt3, kt4 = st.columns(4)
        kt1.metric("📄 Valor Total NFs (Transportadoras)", f"R$ {total_nf_transp:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        kt2.metric("🚚 Custo Total Frete (Transportadoras)", f"R$ {total_fr_transp:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        kt3.metric("📊 % Médio Frete / Valor NFs", f"{pct_medio_transp:.2f}%")
        kt4.metric(
            "🏆 Maior Custo Transportadora",
            top_transp_nome[:22],
            delta=f"R$ {top_transp_val:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            delta_color="off",
        )

        top_n_opcoes = [10, 15, 20, len(df_mnop_clean)]
        top_n_labels = ["Top 10 Transportadoras", "Top 15 Transportadoras", "Top 20 Transportadoras", "Todas as Transportadoras"]
        sel_top_idx = st.selectbox(
            "Exibir no gráfico comparativo:",
            range(len(top_n_labels)),
            format_func=lambda i: top_n_labels[i],
            index=0,
            key="sel_top_transp_comp",
        )
        limite_transp = top_n_opcoes[sel_top_idx]

        df_plot_tr = df_mnop_clean.head(limite_transp).copy().reset_index(drop=True)
        eixo_x_tr = df_plot_tr["Transportadora"].tolist()
        y_nf_tr = df_plot_tr["Valor_NF"].tolist()
        y_fr_tr = df_plot_tr["Valor_Frete"].tolist()
        pct_tr_list = (df_plot_tr["Pct_Frete"] * 100).tolist()

        max_val_tr = max(max(y_nf_tr, default=100), max(y_fr_tr, default=100))

        fig_tr_comp = go.Figure()

        fig_tr_comp.add_trace(
            go.Bar(
                x=eixo_x_tr,
                y=y_nf_tr,
                name="Valor Total NFs (R$)",
                marker=dict(color="#1f77b4", line=dict(color="#000000", width=1.0)),
                text=[f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") for v in y_nf_tr],
                textposition="outside",
                textfont=dict(size=10, color="#000000"),
                cliponaxis=False,
                hovertemplate="<b>%{x}</b><br>Vlr. Nota Fiscal: R$ %{y:,.2f}<extra></extra>",
            )
        )

        fig_tr_comp.add_trace(
            go.Bar(
                x=eixo_x_tr,
                y=y_fr_tr,
                name="Custo de Frete (R$)",
                marker=dict(color="#d62728", line=dict(color="#000000", width=1.0)),
                text=[f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") for v in y_fr_tr],
                textposition="outside",
                textfont=dict(size=10, color="#000000"),
                cliponaxis=False,
                hovertemplate="<b>%{x}</b><br>VL. FRETE: R$ %{y:,.2f}<extra></extra>",
            )
        )

        y_topo_tr = max_val_tr * 1.25

        for tr_nome, p_tr in zip(eixo_x_tr, pct_tr_list):
            fig_tr_comp.add_annotation(
                x=tr_nome,
                y=y_topo_tr,
                text=f"<b>% Frete: {p_tr:.1f}%</b>",
                showarrow=False,
                font=dict(size=11, color="#d62728", family="Arial Black"),
                bgcolor="#f8d7da",
                bordercolor="#f5c6cb",
                borderwidth=1,
                borderpad=5,
            )

        fig_tr_comp.update_layout(
            template="plotly_white",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#000000", size=12, family="Arial"),
            margin=dict(l=50, r=50, t=70, b=110),
            height=580,
            barmode="group",
            bargap=0.25,
            yaxis=dict(
                title=dict(text="<b>Valor Monetário (R$)</b>", font=dict(size=13, color="#000000")),
                showgrid=True,
                gridcolor="#e9ecef",
                range=[0, max_val_tr * 1.42],
            ),
            xaxis=dict(type="category", tickangle=-25, tickfont=dict(size=10, color="#000000")),
            legend=dict(orientation="h", y=1.14, x=1, xanchor="right", font=dict(size=12, color="#000000")),
        )

        st.plotly_chart(fig_tr_comp, use_container_width=True)