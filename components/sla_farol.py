import pandas as pd
import plotly.graph_objects as go
import streamlit as st


def _classificar_farol(pct_sla: float, total_concluidas: int) -> str:
    if total_concluidas == 0:
        return "⚪ Sem Retorno"
    if pct_sla >= 85.0:
        return "🟢 No Prazo (≥85%)"
    if pct_sla >= 70.0:
        return "🟡 Atenção (70%–84,9%)"
    return "🔴 Crítico (<70%)"


def render_secao_sla(df_sla: pd.DataFrame, df_pedidos_brutos: pd.DataFrame):
    st.markdown("### 🚦 Farol SLA de Entregas & Acompanhamento Operacional")

    if df_sla is None or df_sla.empty:
        st.info("📂 **Aguardando base SLA:** Insira o arquivo `SLA.xls` na pasta `./data/` para visualizar os indicadores.")
        return

    # =========================================================================
    # REGRA OFICIAL:
    # 1. Considerar APENAS as notas que possuem "Dt. Romaneio"
    # 2. As que possuem "Dt. Entrega Real" -> calcular SLA (Dt_Entrega_Real <= Dt_Previsao)
    # 3. Caso contrário (sem "Dt. Entrega Real") -> KPI "Pendência de retorno"
    # =========================================================================
    df_rom = df_sla.dropna(subset=["Dt_Romaneio"]).copy()

    if df_rom.empty:
        st.warning("Nenhuma nota com 'Dt. Romaneio' preenchida encontrada na planilha SLA.")
        return

    # Filtros da aba SLA
    col_f1, col_f2, col_f3 = st.columns([1.6, 1.4, 1.4])

    min_dt = df_rom["Dt_Romaneio"].min().date()
    max_dt = df_rom["Dt_Romaneio"].max().date()

    with col_f1:
        periodo_sla = st.date_input(
            "📅 Período (Dt. Romaneio):",
            value=(min_dt, max_dt),
            min_value=min_dt,
            max_value=max_dt,
            key="sla_periodo_romaneio",
        )
        dt_ini_s, dt_fim_s = (
            periodo_sla if isinstance(periodo_sla, tuple) and len(periodo_sla) == 2 else (min_dt, max_dt)
        )

    df_filtrado = df_rom[
        (df_rom["Dt_Romaneio"].dt.date >= dt_ini_s) & (df_rom["Dt_Romaneio"].dt.date <= dt_fim_s)
    ].copy()

    with col_f2:
        lista_transp = ["Todas as Transportadoras"] + sorted(df_filtrado["Transport."].dropna().unique().tolist())
        transp_sel = st.selectbox("🚚 Filtrar Transportadora:", lista_transp, index=0, key="sla_transp_sel")

    if transp_sel != "Todas as Transportadoras":
        df_filtrado = df_filtrado[df_filtrado["Transport."] == transp_sel].copy()

    with col_f3:
        lista_clientes = ["Todos os Clientes"] + sorted(df_filtrado["Cliente"].dropna().unique().tolist())
        cliente_sel = st.selectbox("🏥 Filtrar Cliente:", lista_clientes, index=0, key="sla_cliente_sel")

    if cliente_sel != "Todos os Clientes":
        df_filtrado = df_filtrado[df_filtrado["Cliente"] == cliente_sel].copy()

    # Classificação linha a linha
    df_filtrado["Tem_Entrega"] = df_filtrado["Dt_Entrega_Real"].notna()
    df_filtrado["Tem_Previsao"] = df_filtrado["Dt_Previsao"].notna()

    # Considera no prazo quando Dt_Entrega_Real <= Dt_Previsao (ou quando Dt_Previsao não foi preenchida no ERP)
    df_filtrado["No_Prazo"] = df_filtrado["Tem_Entrega"] & (
        (~df_filtrado["Tem_Previsao"]) | (df_filtrado["Dt_Entrega_Real"] <= df_filtrado["Dt_Previsao"])
    )
    df_filtrado["Fora_Prazo"] = df_filtrado["Tem_Entrega"] & df_filtrado["Tem_Previsao"] & (
        df_filtrado["Dt_Entrega_Real"] > df_filtrado["Dt_Previsao"]
    )
    df_filtrado["Pendencia_Retorno"] = ~df_filtrado["Tem_Entrega"]

    def _status_linha(row):
        if row["Pendencia_Retorno"]:
            return "⏳ Pendência de Retorno"
        if row["No_Prazo"]:
            return "🟢 No Prazo"
        return "🔴 Fora do Prazo"

    df_filtrado["Status_SLA"] = df_filtrado.apply(_status_linha, axis=1)

    # =========================================================================
    # 1. KPIs PRINCIPAIS DO SLA
    # =========================================================================
    total_expedidas = len(df_filtrado)
    total_entregues = int(df_filtrado["Tem_Entrega"].sum())
    total_no_prazo = int(df_filtrado["No_Prazo"].sum())
    total_fora_prazo = int(df_filtrado["Fora_Prazo"].sum())
    total_pendencia = int(df_filtrado["Pendencia_Retorno"].sum())

    pct_sla_geral = (total_no_prazo / total_entregues * 100) if total_entregues > 0 else 0.0
    pct_pendencia = (total_pendencia / total_expedidas * 100) if total_expedidas > 0 else 0.0

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("📦 NFs Expedidas (c/ Romaneio)", f"{total_expedidas:,}".replace(",", "."))
    k2.metric("✅ Entregas Concluídas", f"{total_entregues:,}".replace(",", "."))
    k3.metric("🎯 % SLA No Prazo", f"{pct_sla_geral:.2f}%", delta=f"{total_no_prazo:,} no prazo".replace(",", "."), delta_color="normal")
    k4.metric("🚨 Entregas Fora do Prazo", f"{total_fora_prazo:,}".replace(",", "."))
    k5.metric(
        "⏳ Pendência de Retorno",
        f"{total_pendencia:,}".replace(",", "."),
        delta=f"{pct_pendencia:.1f}% sem baixa",
        delta_color="inverse",
    )

    # =========================================================================
    # 2. GRÁFICOS DE DESEMPENHO SLA (DIÁRIO E POR TRANSPORTADORA)
    # =========================================================================
    st.markdown("---")
    col_g1, col_g2 = st.columns([1.4, 1.1])

    with col_g1:
        st.markdown("#### 📈 Evolução Diária: No Prazo vs. Fora do Prazo vs. Pendência de Retorno")
        df_dia = (
            df_filtrado.groupby("Dt_Romaneio", as_index=False)
            .agg(
                No_Prazo=("No_Prazo", "sum"),
                Fora_Prazo=("Fora_Prazo", "sum"),
                Pendencia=("Pendencia_Retorno", "sum"),
            )
            .sort_values("Dt_Romaneio")
            .tail(30)
            .reset_index(drop=True)
        )
        df_dia["Data_Str"] = df_dia["Dt_Romaneio"].dt.strftime("%d/%m")

        fig_dia = go.Figure()
        fig_dia.add_trace(
            go.Bar(
                x=df_dia["Data_Str"],
                y=df_dia["No_Prazo"],
                name="No Prazo",
                marker_color="#2ca02c",
                hovertemplate="<b>%{x}</b><br>No Prazo: %{y}<extra></extra>",
            )
        )
        fig_dia.add_trace(
            go.Bar(
                x=df_dia["Data_Str"],
                y=df_dia["Fora_Prazo"],
                name="Fora do Prazo",
                marker_color="#d62728",
                hovertemplate="<b>%{x}</b><br>Fora do Prazo: %{y}<extra></extra>",
            )
        )
        fig_dia.add_trace(
            go.Bar(
                x=df_dia["Data_Str"],
                y=df_dia["Pendencia"],
                name="Pendência de Retorno",
                marker_color="#ff9f1c",
                hovertemplate="<b>%{x}</b><br>Pendência Retorno: %{y}<extra></extra>",
            )
        )
        fig_dia.update_layout(
            template="plotly_white",
            barmode="stack",
            height=420,
            margin=dict(l=30, r=20, t=40, b=40),
            xaxis=dict(type="category", tickangle=-35),
            yaxis=dict(title="<b>Qtd. Notas Fiscais</b>", gridcolor="#e9ecef"),
            legend=dict(orientation="h", y=1.12, x=1, xanchor="right"),
        )
        st.plotly_chart(fig_dia, use_container_width=True)

    with col_g2:
        st.markdown("#### 🚚 SLA & Pendências por Transportadora (Top 10)")
        df_tr_sla = (
            df_filtrado.groupby("Transport.", as_index=False)
            .agg(
                Expedidas=("NF_Str", "count"),
                Entregues=("Tem_Entrega", "sum"),
                No_Prazo=("No_Prazo", "sum"),
                Pendencia=("Pendencia_Retorno", "sum"),
            )
            .sort_values("Expedidas", ascending=False)
            .head(10)
            .reset_index(drop=True)
        )
        df_tr_sla["Pct_SLA"] = (df_tr_sla["No_Prazo"] / df_tr_sla["Entregues"].replace(0, pd.NA) * 100).fillna(0.0)

        fig_tr = go.Figure()
        fig_tr.add_trace(
            go.Bar(
                y=df_tr_sla["Transport."],
                x=df_tr_sla["Pct_SLA"],
                orientation="h",
                marker=dict(
                    color=[
                        "#2ca02c" if p >= 85 else ("#ff9f1c" if p >= 70 else "#d62728")
                        for p in df_tr_sla["Pct_SLA"]
                    ],
                    line=dict(color="#000000", width=0.8),
                ),
                text=[f"<b>{p:.1f}%</b> ({int(np)}/{int(ent)})" for p, np, ent in zip(df_tr_sla["Pct_SLA"], df_tr_sla["No_Prazo"], df_tr_sla["Entregues"])],
                textposition="outside",
                cliponaxis=False,
                hovertemplate="<b>%{y}</b><br>% SLA: %{x:.2f}%<extra></extra>",
            )
        )
        fig_tr.update_layout(
            template="plotly_white",
            height=420,
            margin=dict(l=140, r=80, t=40, b=40),
            xaxis=dict(title="<b>% SLA No Prazo</b>", range=[0, 125], gridcolor="#e9ecef"),
            yaxis=dict(autorange="reversed"),
        )
        st.plotly_chart(fig_tr, use_container_width=True)

    # =========================================================================
    # 3. FAROL SLA POR CLIENTE (JANELA DE ENTREGA E SEMÁFORO)
    # =========================================================================
    st.markdown("---")
    st.markdown("### 🚦 Farol SLA por Cliente (Janela de Entrega & Pendências de Retorno)")

    df_cli_sla = (
        df_filtrado.groupby("Cliente", as_index=False)
        .agg(
            NFs_Expedidas=("NF_Str", "count"),
            Entregas_Realizadas=("Tem_Entrega", "sum"),
            No_Prazo=("No_Prazo", "sum"),
            Fora_Prazo=("Fora_Prazo", "sum"),
            Pendencia_Retorno=("Pendencia_Retorno", "sum"),
        )
        .sort_values("NFs_Expedidas", ascending=False)
        .reset_index(drop=True)
    )

    df_cli_sla["Pct_SLA"] = (
        df_cli_sla["No_Prazo"] / df_cli_sla["Entregas_Realizadas"].replace(0, pd.NA) * 100
    ).fillna(0.0)

    df_cli_sla["Farol_SLA"] = [
        _classificar_farol(pct, int(ent))
        for pct, ent in zip(df_cli_sla["Pct_SLA"], df_cli_sla["Entregas_Realizadas"])
    ]
    df_cli_sla["Pct_SLA_Str"] = [
        f"{pct:.2f}%" if int(ent) > 0 else "Aguardando Retorno"
        for pct, ent in zip(df_cli_sla["Pct_SLA"], df_cli_sla["Entregas_Realizadas"])
    ]

    col_fc1, col_fc2 = st.columns([2, 2])
    with col_fc1:
        filtro_farol = st.multiselect(
            "Filtrar por Status do Farol:",
            ["🟢 No Prazo (≥85%)", "🟡 Atenção (70%–84,9%)", "🔴 Crítico (<70%)", "⚪ Sem Retorno"],
            default=["🟢 No Prazo (≥85%)", "🟡 Atenção (70%–84,9%)", "🔴 Crítico (<70%)", "⚪ Sem Retorno"],
            key="sla_farol_multiselect",
        )
    with col_fc2:
        busca_cli = st.text_input("🔍 Buscar Cliente:", "", key="sla_busca_cliente")

    df_farol_view = df_cli_sla[df_cli_sla["Farol_SLA"].isin(filtro_farol)].copy()
    if busca_cli.strip():
        df_farol_view = df_farol_view[
            df_farol_view["Cliente"].str.contains(busca_cli.strip().upper(), na=False)
        ]

    tabela_farol_exibicao = df_farol_view[
        [
            "Farol_SLA",
            "Cliente",
            "NFs_Expedidas",
            "Entregas_Realizadas",
            "No_Prazo",
            "Fora_Prazo",
            "Pendencia_Retorno",
            "Pct_SLA_Str",
        ]
    ].rename(
        columns={
            "Farol_SLA": "Farol SLA",
            "NFs_Expedidas": "NFs Expedidas",
            "Entregas_Realizadas": "Entregas Realizadas",
            "No_Prazo": "No Prazo",
            "Fora_Prazo": "Fora do Prazo",
            "Pendencia_Retorno": "Pendência de Retorno",
            "Pct_SLA_Str": "% SLA Cumprido",
        }
    )

    st.dataframe(tabela_farol_exibicao, use_container_width=True, height=400)

    # =========================================================================
    # 4. ACOMPANHAMENTO DE PRODUÇÃO DO DIA: REGULAR VS. EMERGENCIAL
    # =========================================================================
    st.markdown("---")
    st.markdown("### ⚡ Acompanhamento de Pedidos em Produção & Monitoramento de Urgências")

    if df_pedidos_brutos is not None and not df_pedidos_brutos.empty:
        datas_disp = sorted(df_pedidos_brutos["DATA"].dropna().unique(), reverse=True)
        data_ref_prod = st.selectbox(
            "📅 Selecione a Data de Produção para Acompanhamento dos Pedidos:",
            datas_disp,
            index=0,
            format_func=lambda d: pd.to_datetime(d).strftime("%d/%m/%Y"),
            key="sla_data_prod_dia",
        )

        df_dia_prod = df_pedidos_brutos[df_pedidos_brutos["DATA"] == data_ref_prod].copy()

        # Classifica fluxo Regular vs. Emergencial / Prioritário (pedidos críticos em backlog/falta ou prioridade)
        def _classificar_fluxo(row):
            st_prod = str(row.get("STATUS PRODUÇÃO", "")).upper()
            st_geral = str(row.get("STATUS", "")).upper()
            if "FALTANDO" in st_prod or "BACKLOG" in st_geral or "EMERG" in st_geral or "URG" in st_geral:
                return "🚨 Emergencial / Prioritário"
            return "✅ Fluxo Regular"

        df_dia_prod["Tipo_Fluxo"] = df_dia_prod.apply(_classificar_fluxo, axis=1)

        tot_ped_dia = len(df_dia_prod)
        qtd_regular = int((df_dia_prod["Tipo_Fluxo"] == "✅ Fluxo Regular").sum())
        qtd_emerg = int((df_dia_prod["Tipo_Fluxo"] == "🚨 Emergencial / Prioritário").sum())
        pct_emerg = (qtd_emerg / tot_ped_dia * 100) if tot_ped_dia > 0 else 0.0

        p1, p2, p3, p4 = st.columns(4)
        p1.metric("📋 Pedidos em Operação no Dia", f"{tot_ped_dia:,}".replace(",", "."))
        p2.metric("✅ Fluxo Regular", f"{qtd_regular:,}".replace(",", "."))
        p3.metric("🚨 Emergencial / Prioritário", f"{qtd_emerg:,}".replace(",", "."))
        p4.metric("⚠️ % Urgência na Operação", f"{pct_emerg:.1f}%")

        cols_prod_show = [c for c in ["Tipo_Fluxo", "PV", "SEPARADOR", "SKU'S", "TR ou NC", "STATUS PRODUÇÃO", "STATUS"] if c in df_dia_prod.columns]
        st.dataframe(
            df_dia_prod[cols_prod_show].rename(
                columns={
                    "Tipo_Fluxo": "Classificação Fluxo",
                    "PV": "Nº Pedido (PV)",
                    "SEPARADOR": "Separador",
                    "SKU'S": "Qtd. SKUs",
                    "TR ou NC": "Transportadora / Modal",
                    "STATUS PRODUÇÃO": "Etapa Produção",
                    "STATUS": "Status Carteira",
                }
            ),
            use_container_width=True,
            height=360,
        )
    else:
        st.info("Base `DadosBrutos` de `DadosProducao.xlsx` não encontrada para detalhamento dos pedidos do dia.")

    # =========================================================================
    # 5. DETALHAMENTO DAS NOTAS COM PENDÊNCIA DE RETORNO
    # =========================================================================
    with st.expander("⏳ Ver Detalhamento das Notas com Pendência de Retorno (Sem Dt. Entrega Real)"):
        df_pend_view = df_filtrado[df_filtrado["Pendencia_Retorno"]].copy()
        if df_pend_view.empty:
            st.success("Nenhuma nota com pendência de retorno no filtro selecionado!")
        else:
            df_pend_view["Previsão"] = df_pend_view["Dt_Previsao"].dt.strftime("%d/%m/%Y").fillna("Sem Previsão")
            df_pend_view["Romaneio"] = df_pend_view["Dt_Romaneio"].dt.strftime("%d/%m/%Y")
            st.dataframe(
                df_pend_view[["NF_Str", "Cliente", "Transport.", "Romaneio", "Previsão", "Status_SLA"]].rename(
                    columns={
                        "NF_Str": "Nota Fiscal",
                        "Transport.": "Transportadora",
                        "Romaneio": "Dt. Romaneio",
                        "Previsão": "Previsão de Entrega",
                        "Status_SLA": "Situação",
                    }
                ),
                use_container_width=True,
                height=320,
            )