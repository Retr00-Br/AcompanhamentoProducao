import pandas as pd
import plotly.graph_objects as go
import streamlit as st


CORES_UNIDADES = {
    "0101 - Matriz": "#1f77b4",
    "0102 - Filial RJ": "#ff7f0e",
    "0103 - Filial CP": "#2ca02c",
    "0104 - Filial SBC": "#9467bd",
    "0106 - Filial 106": "#0284c7",
}


def render_secao_expedicao_geral(df_exp_geral: pd.DataFrame):
    st.markdown("## 🚚 Expedição Geral — Análise por Filial, Matriz & Cliente")

    if df_exp_geral is None or df_exp_geral.empty:
        st.info("📂 **Aguardando base:** Insira a planilha `ExpedicaoGeral.xlsx` na pasta `./data/` para visualizar os indicadores.")
        return

    df_work = df_exp_geral.copy()
    df_work["DATA"] = pd.to_datetime(df_work["DATA"], errors="coerce").dt.normalize()
    df_work = df_work.dropna(subset=["DATA"]).sort_values("DATA").reset_index(drop=True)

    # =========================================================================
    # 1. FILTRO TEMPORAL (CALENDÁRIO ESPECÍFICO, POR MÊS E POR SEMANA)
    # =========================================================================
    st.subheader("📅 Filtro Temporal — Expedição Geral")

    col_ft1, col_ft2 = st.columns([1.5, 3])
    with col_ft1:
        tipo_filtro = st.radio(
            "Filtrar período por:",
            ["Intervalo de Calendário", "Por Mês", "Por Semana do Ano"],
            horizontal=True,
            key="exp_geral_filtro_radio",
        )

    min_date = df_work["DATA"].min().date()
    max_date = df_work["DATA"].max().date()

    with col_ft2:
        if tipo_filtro == "Intervalo de Calendário":
            data_sel = st.date_input(
                "Selecione o Período:",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date,
                key="exp_geral_filtro_dates",
            )
            dt_inicio, dt_fim = (
                data_sel if isinstance(data_sel, tuple) and len(data_sel) == 2 else (min_date, max_date)
            )
        elif tipo_filtro == "Por Mês":
            df_work["Mes_Ano"] = df_work["DATA"].dt.strftime("%Y-%m")
            meses = sorted(df_work["Mes_Ano"].unique().tolist())
            mes_sel = st.selectbox("Selecione o Mês:", meses, index=len(meses) - 1, key="exp_geral_filtro_mes")
            dt_inicio = df_work[df_work["Mes_Ano"] == mes_sel]["DATA"].min().date()
            dt_fim = df_work[df_work["Mes_Ano"] == mes_sel]["DATA"].max().date()
        else:
            df_work["Semana_Inicio"] = df_work["DATA"].apply(lambda d: d - pd.Timedelta(days=d.weekday()))
            df_work["Semana_Fim"] = df_work["Semana_Inicio"] + pd.Timedelta(days=6)
            df_work["Semana_Label"] = (
                "Semana do dia "
                + df_work["Semana_Inicio"].dt.strftime("%d/%m")
                + " - "
                + df_work["Semana_Fim"].dt.strftime("%d/%m")
            )
            semanas = df_work.sort_values("Semana_Inicio")["Semana_Label"].unique().tolist()
            semana_sel = st.selectbox("Selecione a Semana:", semanas, index=len(semanas) - 1, key="exp_geral_filtro_sem")
            dt_inicio = df_work[df_work["Semana_Label"] == semana_sel]["DATA"].min().date()
            dt_fim = df_work[df_work["Semana_Label"] == semana_sel]["DATA"].max().date()

    df_periodo = df_work[
        (df_work["DATA"].dt.date >= dt_inicio) & (df_work["DATA"].dt.date <= dt_fim)
    ].copy().reset_index(drop=True)

    # Filtros de Filial/Matriz e Cliente
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        opcoes_filiais = ["Todas as Unidades (Matriz + Filiais)"] + sorted(
            df_periodo["Filial_Nome"].dropna().unique().tolist()
        )
        filial_sel = st.selectbox(
            "🏢 Filtrar por Matriz / Filial:",
            options=opcoes_filiais,
            index=0,
            key="exp_geral_filial_sel",
        )

    df_filtrado = df_periodo.copy()
    if filial_sel != "Todas as Unidades (Matriz + Filiais)":
        df_filtrado = df_filtrado[df_filtrado["Filial_Nome"] == filial_sel].copy()

    with col_f2:
        opcoes_clientes = ["Todos os Clientes"] + sorted(df_filtrado["Cliente"].dropna().unique().tolist())
        cliente_sel = st.selectbox(
            "🏥 Filtrar por Cliente (Nome Fantasia):",
            options=opcoes_clientes,
            index=0,
            key="exp_geral_cliente_sel",
        )

    if cliente_sel != "Todos os Clientes":
        df_filtrado = df_filtrado[df_filtrado["Cliente"] == cliente_sel].copy()

    if df_filtrado.empty:
        st.warning("Nenhum registro de expedição encontrado para os filtros selecionados.")
        return

    # =========================================================================
    # 2. KPIs COMPLETOS (TOTAIS, MÉDIAS E EXTREMOS DO PERÍODO)
    # =========================================================================
    total_nfs = len(df_filtrado)
    total_pvs = int((df_filtrado["Num.PV"] != "-").sum())
    clientes_ativos = df_filtrado["Cliente"].nunique()

    df_por_dia = df_filtrado.groupby("DATA", as_index=False)["Num.NF"].count().rename(columns={"Num.NF": "Qtd"})
    dias_ativos = max(len(df_por_dia), 1)
    media_dia = total_nfs / dias_ativos

    r_max_d = df_por_dia.loc[df_por_dia["Qtd"].idxmax()]
    r_min_d = df_por_dia.loc[df_por_dia["Qtd"].idxmin()]

    df_por_cli = (
        df_filtrado.groupby("Cliente", as_index=False)["Num.NF"]
        .count()
        .rename(columns={"Num.NF": "Qtd"})
        .sort_values("Qtd", ascending=False)
        .reset_index(drop=True)
    )
    top_cli = df_por_cli.iloc[0]
    bot_cli = df_por_cli.iloc[-1]

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("📦 Total de NFs Expedidas", f"{total_nfs:,}".replace(",", "."), delta=f"{total_pvs:,} PVs vinculados".replace(",", "."), delta_color="off")
    k2.metric("📊 Média Diária de Expedição", f"{media_dia:,.1f}".replace(",", "."), delta=f"{dias_ativos} dias operacionais", delta_color="off")
    k3.metric("🏥 Clientes Atendidos", f"{clientes_ativos:,}".replace(",", "."))
    k4.metric("🏢 Unidades Ativas", f"{df_filtrado['Filial_Nome'].nunique()} unidade(s)")

    st.markdown("<div style='margin-top: 6px;'></div>", unsafe_allow_html=True)
    e1, e2, e3, e4 = st.columns(4)
    e1.metric(
        "🚀 Dia c/ Maior Expedição",
        pd.to_datetime(r_max_d["DATA"]).strftime("%d/%m/%Y"),
        delta=f"{int(r_max_d['Qtd']):,} NFs".replace(",", "."),
        delta_color="normal",
    )
    e2.metric(
        "📉 Dia c/ Menor Expedição",
        pd.to_datetime(r_min_d["DATA"]).strftime("%d/%m/%Y"),
        delta=f"{int(r_min_d['Qtd']):,} NFs".replace(",", "."),
        delta_color="inverse",
    )
    e3.metric(
        "🏆 Cliente c/ Maior Volume",
        str(top_cli["Cliente"])[:24],
        delta=f"{int(top_cli['Qtd']):,} NFs".replace(",", "."),
        delta_color="normal",
    )
    e4.metric(
        "🔻 Cliente c/ Menor Volume",
        str(bot_cli["Cliente"])[:24],
        delta=f"{int(bot_cli['Qtd']):,} NFs".replace(",", "."),
        delta_color="inverse",
    )

    # =========================================================================
    # 3. EVOLUÇÃO DIÁRIA DA EXPEDIÇÃO NO PERÍODO
    # =========================================================================
    st.markdown("---")
    st.markdown("### 📈 Evolução Diária de Expedições (Qtd. Notas Fiscais)")

    df_por_dia["Data_Str"] = df_por_dia["DATA"].dt.strftime("%d/%m")
    max_d = max(int(df_por_dia["Qtd"].max()), 10)

    fig_dia = go.Figure(
        go.Bar(
            x=df_por_dia["Data_Str"],
            y=df_por_dia["Qtd"],
            name="NFs Expedidas",
            marker=dict(color="#ff7f0e", line=dict(color="#000000", width=0.8)),
            text=[str(int(v)) for v in df_por_dia["Qtd"]],
            textposition="outside",
            textfont=dict(size=10, color="#000000", family="Arial Black"),
            cliponaxis=False,
            hovertemplate="<b>Data: %{x}</b><br>NFs Expedidas: %{y}<extra></extra>",
        )
    )
    fig_dia.update_layout(
        template="plotly_white",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#000000", size=12, family="Arial"),
        height=440,
        margin=dict(l=45, r=30, t=40, b=55),
        xaxis=dict(type="category", tickangle=-35, tickfont=dict(size=11, color="#000000")),
        yaxis=dict(
            title=dict(text="<b>Qtd. Notas Fiscais Expedidas</b>", font=dict(size=13, color="#000000")),
            showgrid=True,
            gridcolor="#e9ecef",
            range=[0, max_d * 1.24],
        ),
    )
    st.plotly_chart(fig_dia, use_container_width=True)

    # =========================================================================
    # 4. TOTAL DE EXPEDIÇÕES POR MATRIZ E FILIAIS & TOTAL MENSAL
    # =========================================================================
    st.markdown("---")
    col_u1, col_u2 = st.columns(2)

    with col_u1:
        st.markdown("### 🏢 Total de Expedições por Matriz & Filiais (Período)")
        df_fil_tot = (
            df_periodo.groupby("Filial_Nome", as_index=False)["Num.NF"]
            .count()
            .rename(columns={"Num.NF": "Qtd"})
            .sort_values("Qtd", ascending=False)
            .reset_index(drop=True)
        )
        tot_p_all = max(int(df_fil_tot["Qtd"].sum()), 1)
        max_f = max(int(df_fil_tot["Qtd"].max()), 10)

        fig_fil = go.Figure(
            go.Bar(
                x=df_fil_tot["Filial_Nome"],
                y=df_fil_tot["Qtd"],
                marker=dict(
                    color=[CORES_UNIDADES.get(u, "#64748b") for u in df_fil_tot["Filial_Nome"]],
                    line=dict(color="#000000", width=0.8),
                ),
                text=[f"{int(v):,} ({v / tot_p_all * 100:.1f}%)".replace(",", ".") for v in df_fil_tot["Qtd"]],
                textposition="outside",
                textfont=dict(size=10, color="#000000", family="Arial Black"),
                cliponaxis=False,
                hovertemplate="<b>%{x}</b><br>NFs Expedidas: %{y}<extra></extra>",
            )
        )
        fig_fil.update_layout(
            template="plotly_white",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#000000", size=12, family="Arial"),
            height=430,
            margin=dict(l=40, r=25, t=40, b=45),
            xaxis=dict(type="category", tickfont=dict(size=11, color="#000000")),
            yaxis=dict(
                title=dict(text="<b>Qtd. NFs Expedidas</b>", font=dict(size=12, color="#000000")),
                showgrid=True,
                gridcolor="#e9ecef",
                range=[0, max_f * 1.25],
            ),
        )
        st.plotly_chart(fig_fil, use_container_width=True)

    with col_u2:
        st.markdown("### 📅 Total Mensal Consolidado de Expedições")
        df_base_m = df_work.copy()
        if filial_sel != "Todas as Unidades (Matriz + Filiais)":
            df_base_m = df_base_m[df_base_m["Filial_Nome"] == filial_sel].copy()
        if cliente_sel != "Todos os Clientes":
            df_base_m = df_base_m[df_base_m["Cliente"] == cliente_sel].copy()

        df_base_m["Mes_Ano"] = df_base_m["DATA"].dt.strftime("%Y-%m")
        df_mes_tot = (
            df_base_m.groupby("Mes_Ano", as_index=False)["Num.NF"]
            .count()
            .rename(columns={"Num.NF": "Qtd"})
            .sort_values("Mes_Ano")
            .reset_index(drop=True)
        )
        max_m = max(int(df_mes_tot["Qtd"].max()), 10)

        fig_mes = go.Figure(
            go.Bar(
                x=df_mes_tot["Mes_Ano"],
                y=df_mes_tot["Qtd"],
                marker=dict(color="#16a34a", line=dict(color="#000000", width=0.8)),
                text=[f"{int(v):,}".replace(",", ".") for v in df_mes_tot["Qtd"]],
                textposition="outside",
                textfont=dict(size=10, color="#000000", family="Arial Black"),
                cliponaxis=False,
                hovertemplate="<b>Mês: %{x}</b><br>Total Expedido: %{y}<extra></extra>",
            )
        )
        fig_mes.update_layout(
            template="plotly_white",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#000000", size=12, family="Arial"),
            height=430,
            margin=dict(l=40, r=25, t=40, b=45),
            xaxis=dict(type="category", tickfont=dict(size=11, color="#000000")),
            yaxis=dict(
                title=dict(text="<b>Total Mensal (NFs)</b>", font=dict(size=12, color="#000000")),
                showgrid=True,
                gridcolor="#e9ecef",
                range=[0, max_m * 1.25],
            ),
        )
        st.plotly_chart(fig_mes, use_container_width=True)

    # =========================================================================
    # 5. COMPARATIVO MENSAL: MATRIZ VS. FILIAIS
    # =========================================================================
    st.markdown("---")
    st.markdown("### 📊 Comparativo Mensal de Expedições: Matriz vs. Filiais")

    df_comp_m = df_work.copy()
    if cliente_sel != "Todos os Clientes":
        df_comp_m = df_comp_m[df_comp_m["Cliente"] == cliente_sel].copy()
    df_comp_m["Mes_Ano"] = df_comp_m["DATA"].dt.strftime("%Y-%m")
    df_piv_m = (
        df_comp_m.groupby(["Mes_Ano", "Filial_Nome"], as_index=False)["Num.NF"]
        .count()
        .rename(columns={"Num.NF": "Qtd"})
        .sort_values("Mes_Ano")
    )

    fig_comp_m = go.Figure()
    max_cm = max(int(df_piv_m["Qtd"].max()) if not df_piv_m.empty else 10, 10)
    for unid in sorted(df_piv_m["Filial_Nome"].unique()):
        sub_u = df_piv_m[df_piv_m["Filial_Nome"] == unid]
        fig_comp_m.add_trace(
            go.Bar(
                x=sub_u["Mes_Ano"],
                y=sub_u["Qtd"],
                name=unid,
                marker=dict(color=CORES_UNIDADES.get(unid, "#64748b"), line=dict(color="#000000", width=0.8)),
                text=[f"{int(v):,}".replace(",", ".") for v in sub_u["Qtd"]],
                textposition="outside",
                textfont=dict(size=10, color="#000000", family="Arial Black"),
                cliponaxis=False,
                hovertemplate=f"<b>%{{x}} — {unid}</b><br>NFs Expedidas: %{{y}}<extra></extra>",
            )
        )

    fig_comp_m.update_layout(
        template="plotly_white",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#000000", size=12, family="Arial"),
        height=460,
        margin=dict(l=45, r=30, t=55, b=45),
        barmode="group",
        bargap=0.22,
        xaxis=dict(type="category", tickfont=dict(size=11, color="#000000")),
        yaxis=dict(
            title=dict(text="<b>Qtd. NFs Expedidas por Unidade</b>", font=dict(size=13, color="#000000")),
            showgrid=True,
            gridcolor="#e9ecef",
            range=[0, max_cm * 1.26],
        ),
        legend=dict(orientation="h", y=1.12, x=1, xanchor="right", font=dict(size=12, color="#000000")),
    )
    st.plotly_chart(fig_comp_m, use_container_width=True)

    # =========================================================================
    # 6. TOP 10 CLIENTES EXPEDIDOS & TABELA AUDITÁVEL DE ROMANEIOS
    # =========================================================================
    st.markdown("---")
    col_t1, col_t2 = st.columns([1.2, 1.2])

    with col_t1:
        st.markdown("### 🏆 Top 10 Clientes por Volume de NFs Expedidas")
        df_top10 = (
            df_filtrado.groupby(["Cliente", "Filial_Nome"], as_index=False)["Num.NF"]
            .count()
            .rename(columns={"Num.NF": "Qtd_NFs"})
            .sort_values("Qtd_NFs", ascending=False)
            .head(10)
            .reset_index(drop=True)
        )
        df_top10["Label"] = df_top10["Cliente"] + " (" + df_top10["Filial_Nome"].str[:4] + ")"
        max_t10 = max(int(df_top10["Qtd_NFs"].max()), 10)

        fig_t10 = go.Figure(
            go.Bar(
                y=df_top10["Label"],
                x=df_top10["Qtd_NFs"],
                orientation="h",
                marker=dict(color="#1f77b4", line=dict(color="#000000", width=0.8)),
                text=df_top10["Qtd_NFs"],
                textposition="outside",
                textfont=dict(size=10, color="#000000", family="Arial Black"),
                cliponaxis=False,
                hovertemplate="<b>%{y}</b><br>NFs Expedidas: %{x}<extra></extra>",
            )
        )
        fig_t10.update_layout(
            template="plotly_white",
            height=430,
            margin=dict(l=170, r=45, t=30, b=30),
            xaxis=dict(title="<b>Qtd. NFs Expedidas</b>", range=[0, max_t10 * 1.22], gridcolor="#e9ecef"),
            yaxis=dict(autorange="reversed", tickfont=dict(size=10, color="#000000")),
        )
        st.plotly_chart(fig_t10, use_container_width=True)

    with col_t2:
        st.markdown("### 📋 Registro Detalhado de Romaneios & NFs")
        df_tab = df_filtrado.copy()
        df_tab["Dt. Romaneio"] = df_tab["DATA"].dt.strftime("%d/%m/%Y")
        st.dataframe(
            df_tab[["Dt. Romaneio", "Filial_Nome", "Cliente", "Num.PV", "Num.NF"]].rename(
                columns={
                    "Filial_Nome": "Matriz / Filial",
                    "Cliente": "Cliente (Nome Fantasia)",
                    "Num.PV": "Pedido (PV)",
                    "Num.NF": "Nota Fiscal",
                }
            ),
            use_container_width=True,
            height=430,
            hide_index=True,
        )

    # =========================================================================
    # 7. NOVO GRÁFICO: EXPEDIÇÕES POR PERÍODO SELECIONADO (MATRIZ VS. FILIAIS)
    # =========================================================================
    st.markdown("---")
    df_dyn = df_periodo.copy()
    if cliente_sel != "Todos os Clientes":
        df_dyn = df_dyn[df_dyn["Cliente"] == cliente_sel].copy()

    if tipo_filtro == "Por Mês":
        titulo_dyn = f"### 🧭 Expedições no Mês Selecionado ({mes_sel}) — Matriz vs. Filiais (Dia a Dia)"
        df_dyn["Eixo_X"] = df_dyn["DATA"].dt.strftime("%d/%m")
        df_dyn["Ordem_X"] = df_dyn["DATA"]
    elif tipo_filtro == "Por Semana do Ano":
        titulo_dyn = f"### 🧭 Expedições na Semana Selecionada ({semana_sel}) — Matriz vs. Filiais (Dia a Dia)"
        dias_pt = {0: "Seg", 1: "Ter", 2: "Qua", 3: "Qui", 4: "Sex", 5: "Sáb", 6: "Dom"}
        df_dyn["Eixo_X"] = df_dyn["DATA"].dt.strftime("%d/%m") + " (" + df_dyn["DATA"].dt.dayofweek.map(dias_pt) + ")"
        df_dyn["Ordem_X"] = df_dyn["DATA"]
    else:
        titulo_dyn = (
            f"### 🧭 Expedições no Período Selecionado ({dt_inicio.strftime('%d/%m/%Y')} a {dt_fim.strftime('%d/%m/%Y')}) "
            "— Matriz vs. Filiais"
        )
        df_dyn["Eixo_X"] = df_dyn["DATA"].dt.strftime("%d/%m")
        df_dyn["Ordem_X"] = df_dyn["DATA"]

    st.markdown(titulo_dyn)

    df_dyn_grp = (
        df_dyn.groupby(["Ordem_X", "Eixo_X", "Filial_Nome"], as_index=False)["Num.NF"]
        .count()
        .rename(columns={"Num.NF": "Qtd"})
        .sort_values("Ordem_X")
        .reset_index(drop=True)
    )

    if not df_dyn_grp.empty:
        ordem_categorias = df_dyn_grp.drop_duplicates("Eixo_X")["Eixo_X"].tolist()
        max_dyn = max(int(df_dyn_grp["Qtd"].max()), 10)

        fig_dyn = go.Figure()
        for unid in sorted(df_dyn_grp["Filial_Nome"].unique()):
            sub_unid = df_dyn_grp[df_dyn_grp["Filial_Nome"] == unid]
            fig_dyn.add_trace(
                go.Bar(
                    x=sub_unid["Eixo_X"],
                    y=sub_unid["Qtd"],
                    name=unid,
                    marker=dict(color=CORES_UNIDADES.get(unid, "#64748b"), line=dict(color="#000000", width=0.8)),
                    text=[str(int(v)) for v in sub_unid["Qtd"]],
                    textposition="outside",
                    textfont=dict(size=10, color="#000000", family="Arial Black"),
                    cliponaxis=False,
                    hovertemplate=f"<b>%{{x}} — {unid}</b><br>NFs Expedidas: %{{y}}<extra></extra>",
                )
            )

        fig_dyn.update_layout(
            template="plotly_white",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#000000", size=12, family="Arial"),
            height=480,
            margin=dict(l=45, r=30, t=55, b=60),
            barmode="group",
            bargap=0.20,
            xaxis=dict(
                type="category",
                categoryorder="array",
                categoryarray=ordem_categorias,
                tickangle=-35,
                tickfont=dict(size=11, color="#000000"),
            ),
            yaxis=dict(
                title=dict(text="<b>Qtd. NFs Expedidas (Matriz vs. Filiais)</b>", font=dict(size=13, color="#000000")),
                showgrid=True,
                gridcolor="#e9ecef",
                range=[0, max_dyn * 1.26],
            ),
            legend=dict(orientation="h", y=1.12, x=1, xanchor="right", font=dict(size=12, color="#000000")),
        )
        st.plotly_chart(fig_dyn, use_container_width=True)