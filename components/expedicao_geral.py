import pandas as pd
import plotly.graph_objects as go
import streamlit as st


def _fmt_int(val: float) -> str:
    return f"{int(round(val)):,}".replace(",", ".")


def _render_filtro_temporal_exp_geral(df_base: pd.DataFrame) -> pd.DataFrame:
    st.subheader("📅 Filtro Temporal — Expedição Geral")

    if df_base is None or df_base.empty:
        return pd.DataFrame()

    df_work = df_base.copy()
    df_work["DATA"] = pd.to_datetime(df_work["DATA"], errors="coerce").dt.normalize()
    df_work = df_work.dropna(subset=["DATA"]).sort_values("DATA").reset_index(drop=True)

    col_ft1, col_ft2 = st.columns([1.5, 3])

    with col_ft1:
        tipo_filtro = st.radio(
            "Filtrar período por:",
            ["Intervalo de Calendário", "Por Mês", "Por Semana do Ano"],
            horizontal=True,
            key="filtro_tempo_exp_geral_radio",
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
                key="filtro_tempo_exp_geral_dates",
            )
            dt_inicio, dt_fim = (
                data_sel if isinstance(data_sel, tuple) and len(data_sel) == 2 else (min_date, max_date)
            )

        elif tipo_filtro == "Por Mês":
            df_work["Mes_Ano"] = df_work["DATA"].dt.strftime("%Y-%m")
            meses = sorted(df_work["Mes_Ano"].unique().tolist())
            mes_sel = st.selectbox(
                "Selecione o Mês:",
                meses,
                index=len(meses) - 1,
                key="filtro_tempo_exp_geral_mes",
            )
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
            semana_sel = st.selectbox(
                "Selecione a Semana:",
                semanas,
                index=len(semanas) - 1,
                key="filtro_tempo_exp_geral_semana",
            )
            dt_inicio = df_work[df_work["Semana_Label"] == semana_sel]["DATA"].min().date()
            dt_fim = df_work[df_work["Semana_Label"] == semana_sel]["DATA"].max().date()

    df_out = df_work[
        (df_work["DATA"].dt.date >= dt_inicio) & (df_work["DATA"].dt.date <= dt_fim)
    ].copy().sort_values("DATA").reset_index(drop=True)

    df_out["Data_Str"] = df_out["DATA"].dt.strftime("%d/%m")
    return df_out


def render_secao_expedicao_geral(df_exp_geral: pd.DataFrame):
    st.markdown("## 📦 Expedição Geral — Romaneios por Matriz & Filiais")

    if df_exp_geral is None or df_exp_geral.empty:
        st.info("📂 Aguardando dados de `ExpedicaoGeral.xlsx` na pasta `./data/`.")
        return

    df_filtrado = _render_filtro_temporal_exp_geral(df_exp_geral)

    filiais_disp = sorted(df_exp_geral["Filial_Nome"].dropna().unique().tolist())
    opcoes_filiais = ["Todas as Unidades (Geral)"] + filiais_disp

    unidade_sel = st.selectbox(
        "🏢 Filtrar Unidade / Filial (Expedição Geral):",
        options=opcoes_filiais,
        index=0,
        key="unidade_sel_exp_geral",
    )

    df_view = (
        df_filtrado[df_filtrado["Filial_Nome"] == unidade_sel].copy()
        if unidade_sel != "Todas as Unidades (Geral)"
        else df_filtrado.copy()
    )

    if df_view.empty:
        st.warning("Sem registros de expedição para a unidade e período selecionados.")
        return

    # =========================================================================
    # 1. KPIs DE VOLUME E EXTREMOS DO PERÍODO SELECIONADO
    # =========================================================================
    total_expedicoes = len(df_view)
    total_nfs = df_view["Num.NF"].nunique() if "Num.NF" in df_view.columns else total_expedicoes
    total_pvs = (
        df_view[df_view["Num.PV"] != "-"]["Num.PV"].nunique()
        if "Num.PV" in df_view.columns
        else total_expedicoes
    )
    total_clientes = df_view["Cliente"].nunique()

    df_dia_agg = (
        df_view.groupby("DATA", as_index=False)
        .size()
        .rename(columns={"size": "Qtd_Exp"})
        .sort_values("DATA")
        .reset_index(drop=True)
    )
    dias_ativos = max(len(df_dia_agg), 1)
    media_dia = total_expedicoes / dias_ativos

    idx_max_d = df_dia_agg["Qtd_Exp"].idxmax()
    idx_min_d = df_dia_agg["Qtd_Exp"].idxmin()

    dt_max_str = pd.to_datetime(df_dia_agg.loc[idx_max_d, "DATA"]).strftime("%d/%m/%Y")
    val_max_d = int(df_dia_agg.loc[idx_max_d, "Qtd_Exp"])

    dt_min_str = pd.to_datetime(df_dia_agg.loc[idx_min_d, "DATA"]).strftime("%d/%m/%Y")
    val_min_d = int(df_dia_agg.loc[idx_min_d, "Qtd_Exp"])

    df_cli_agg = (
        df_view.groupby("Cliente", as_index=False)
        .size()
        .rename(columns={"size": "Qtd_Exp"})
        .sort_values("Qtd_Exp", ascending=False)
        .reset_index(drop=True)
    )
    cli_top_nome = str(df_cli_agg.iloc[0]["Cliente"])[:26]
    cli_top_qtd = int(df_cli_agg.iloc[0]["Qtd_Exp"])

    cli_bot_nome = str(df_cli_agg.iloc[-1]["Cliente"])[:26]
    cli_bot_qtd = int(df_cli_agg.iloc[-1]["Qtd_Exp"])

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("🚚 Total de Expedições (Romaneios)", _fmt_int(total_expedicoes))
    c2.metric("📊 Média Diária de Expedição", f"{media_dia:,.1f}".replace(",", "."), delta=f"{dias_ativos} dias ativos", delta_color="off")
    c3.metric("🧾 Notas Fiscais (NFs)", _fmt_int(total_nfs))
    c4.metric("📋 Pedidos de Venda (PVs)", _fmt_int(total_pvs))
    c5.metric("🏥 Clientes Atendidos", _fmt_int(total_clientes))

    st.markdown("<div style='margin-top: 8px;'></div>", unsafe_allow_html=True)
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("🚀 Maior Dia de Expedição", dt_max_str, delta=f"{_fmt_int(val_max_d)} expedições", delta_color="normal")
    k2.metric("🐢 Menor Dia de Expedição", dt_min_str, delta=f"{_fmt_int(val_min_d)} expedições", delta_color="off")
    k3.metric("👑 Cliente Maior Volume Expedido", cli_top_nome, delta=f"{_fmt_int(cli_top_qtd)} expedições", delta_color="normal")
    k4.metric("📉 Cliente Menor Volume Expedido", cli_bot_nome, delta=f"{_fmt_int(cli_bot_qtd)} expedições", delta_color="off")

    # =========================================================================
    # 2. GRÁFICO DIÁRIO DE EXPEDIÇÕES NO PERÍODO SELECIONADO
    # =========================================================================
    st.markdown("---")
    st.markdown(f"### 📈 Evolução Diária de Expedições — {unidade_sel}")

    df_dia_agg["Data_Str"] = pd.to_datetime(df_dia_agg["DATA"]).dt.strftime("%d/%m")
    fig_dia = go.Figure(
        go.Bar(
            x=df_dia_agg["Data_Str"],
            y=df_dia_agg["Qtd_Exp"],
            name="Expedições / Dia",
            marker=dict(color="#1f77b4", line=dict(color="#000000", width=0.8)),
            text=[_fmt_int(v) if v > 0 else "" for v in df_dia_agg["Qtd_Exp"]],
            textposition="outside",
            textfont=dict(size=10, color="#000000", family="Arial Black"),
            cliponaxis=False,
            hovertemplate="<b>Data: %{x}</b><br>Expedições: %{y:,.0f}<extra></extra>",
        )
    )
    fig_dia.update_layout(
        template="plotly_white",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#000000", size=12, family="Arial"),
        height=440,
        margin=dict(l=45, r=30, t=45, b=55),
        yaxis=dict(
            title=dict(text="<b>Volume Expedido (Qtd)</b>", font=dict(size=12, color="#000000")),
            showgrid=True,
            gridcolor="#e9ecef",
            range=[0, max(df_dia_agg["Qtd_Exp"].max() * 1.25, 10)],
        ),
        xaxis=dict(type="category", tickangle=-35, tickfont=dict(size=11, color="#000000")),
    )
    st.plotly_chart(fig_dia, use_container_width=True)

    # =========================================================================
    # 3. TOTAL DE EXPEDIÇÕES POR MATRIZ & FILIAIS + COMPARATIVO MENSAL
    # =========================================================================
    st.markdown("---")
    col_g1, col_g2 = st.columns(2)

    with col_g1:
        st.markdown("### 🏢 Total de Expedições por Matriz e Filiais (Período)")
        df_fil_tot = (
            df_filtrado.groupby("Filial_Nome", as_index=False)
            .size()
            .rename(columns={"size": "Total_Exp"})
            .sort_values("Total_Exp", ascending=False)
            .reset_index(drop=True)
        )
        cores_fil = ["#1f77b4", "#16a34a", "#f59e0b", "#7c3aed", "#0284c7"]
        fig_fil = go.Figure(
            go.Bar(
                x=df_fil_tot["Filial_Nome"],
                y=df_fil_tot["Total_Exp"],
                marker=dict(
                    color=[cores_fil[i % len(cores_fil)] for i in range(len(df_fil_tot))],
                    line=dict(color="#000000", width=0.8),
                ),
                text=[_fmt_int(v) for v in df_fil_tot["Total_Exp"]],
                textposition="outside",
                textfont=dict(size=11, color="#000000", family="Arial Black"),
                cliponaxis=False,
                hovertemplate="<b>%{x}</b><br>Total Expedições: %{y:,.0f}<extra></extra>",
            )
        )
        fig_fil.update_layout(
            template="plotly_white",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#000000", size=11, family="Arial"),
            height=430,
            margin=dict(l=45, r=25, t=45, b=50),
            yaxis=dict(
                title=dict(text="<b>Total de Expedições</b>", font=dict(size=12, color="#000000")),
                showgrid=True,
                gridcolor="#e9ecef",
                range=[0, max(df_fil_tot["Total_Exp"].max() * 1.25, 10)],
            ),
            xaxis=dict(type="category", tickfont=dict(size=11, color="#000000")),
        )
        st.plotly_chart(fig_fil, use_container_width=True)

    with col_g2:
        st.markdown("### 📅 Total Mensal & Comparativo Matriz x Filiais")
        df_m = df_exp_geral.copy()
        df_m["DATA"] = pd.to_datetime(df_m["DATA"], errors="coerce").dt.normalize()
        meses_pt = {
            "01": "Jan", "02": "Fev", "03": "Mar", "04": "Abr",
            "05": "Mai", "06": "Jun", "07": "Jul", "08": "Ago",
            "09": "Set", "10": "Out", "11": "Nov", "12": "Dez",
        }
        df_m["Mes_Ord"] = df_m["DATA"].dt.strftime("%Y-%m")
        df_m["Mes_Label"] = df_m["DATA"].apply(
            lambda d: f"{meses_pt.get(d.strftime('%m'), d.strftime('%m'))}/{d.strftime('%Y')}"
        )

        df_m_fil = (
            df_m.groupby(["Mes_Ord", "Mes_Label", "Filial_Nome"], as_index=False)
            .size()
            .rename(columns={"size": "Qtd"})
            .sort_values("Mes_Ord")
        )
        df_m_tot = (
            df_m.groupby(["Mes_Ord", "Mes_Label"], as_index=False)
            .size()
            .rename(columns={"size": "Total_Geral"})
            .sort_values("Mes_Ord")
        )

        fig_mensal = go.Figure()
        fig_mensal.add_trace(
            go.Bar(
                x=df_m_tot["Mes_Label"],
                y=df_m_tot["Total_Geral"],
                name="Total Geral (Mês)",
                marker=dict(color="#0f172a", line=dict(color="#000000", width=0.8)),
                text=[_fmt_int(v) for v in df_m_tot["Total_Geral"]],
                textposition="outside",
                textfont=dict(size=10, color="#000000", family="Arial Black"),
                cliponaxis=False,
                hovertemplate="<b>%{x}</b><br>Total Geral: %{y:,.0f}<extra></extra>",
            )
        )

        for idx_f, fil_nome in enumerate(sorted(df_m["Filial_Nome"].unique().tolist())):
            sub_f = df_m_fil[df_m_fil["Filial_Nome"] == fil_nome]
            fig_mensal.add_trace(
                go.Bar(
                    x=sub_f["Mes_Label"],
                    y=sub_f["Qtd"],
                    name=fil_nome,
                    marker=dict(color=cores_fil[idx_f % len(cores_fil)], line=dict(color="#000000", width=0.7)),
                    text=[_fmt_int(v) for v in sub_f["Qtd"]],
                    textposition="outside",
                    textfont=dict(size=9, color="#000000", family="Arial Black"),
                    cliponaxis=False,
                    hovertemplate=f"<b>%{{x}}</b><br>{fil_nome}: %{{y:,.0f}}<extra></extra>",
                )
            )

        fig_mensal.update_layout(
            template="plotly_white",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#000000", size=11, family="Arial"),
            height=430,
            margin=dict(l=45, r=25, t=55, b=50),
            barmode="group",
            bargap=0.18,
            yaxis=dict(
                title=dict(text="<b>Expedições no Mês</b>", font=dict(size=12, color="#000000")),
                showgrid=True,
                gridcolor="#e9ecef",
                range=[0, max(df_m_tot["Total_Geral"].max() * 1.26, 10)],
            ),
            xaxis=dict(type="category", tickfont=dict(size=11, color="#000000")),
            legend=dict(orientation="h", y=1.15, x=0.0, xanchor="left", font=dict(size=10, color="#000000")),
        )
        st.plotly_chart(fig_mensal, use_container_width=True)

    # =========================================================================
    # 4. TABELA DETALHADA DE ROMANEIOS DO PERÍODO
    # =========================================================================
    st.markdown("---")
    st.markdown("### 📋 Detalhamento dos Romaneios Expedidos")
    df_tab = df_view.copy()
    df_tab["Data"] = pd.to_datetime(df_tab["DATA"]).dt.strftime("%d/%m/%Y")
    st.dataframe(
        df_tab[["Data", "Filial_Nome", "Cliente", "Num.PV", "Num.NF"]].rename(
            columns={
                "Data": "Dt. Romaneio",
                "Filial_Nome": "Unidade / Filial",
                "Cliente": "Cliente (Nome Fantasia)",
                "Num.PV": "Nº PV",
                "Num.NF": "Nº NF",
            }
        ),
        use_container_width=True,
        height=400,
        hide_index=True,
    )