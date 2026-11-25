import pandas as pd
import plotly.express as px
import streamlit as st


def render_secao_expedicao_geral(df_exp_geral: pd.DataFrame) -> None:
    """Renderiza a aba 📦 Expedição Geral com filtros por filial, período, KPIs e rastreio de PV/NF."""
    st.subheader("📦 Expedição Geral — Consolidado por Unidade")

    if df_exp_geral is None or df_exp_geral.empty:
        st.warning("⚠️ Nenhum dado encontrado em `data/ExpedicaoGeral.xlsx`.")
        return

    df = df_exp_geral.copy()

    # Filtros superiores
    col_f1, col_f2, col_f3 = st.columns([1.5, 1.5, 2])

    with col_f1:
        filiais_disp = ["Todas as Filiais"] + sorted(df["Filial_Norm"].dropna().unique().tolist())
        filial_sel = st.selectbox("🏢 Filtrar por Filial:", filiais_disp, key="exp_geral_filial")

    with col_f2:
        busca_doc = st.text_input("🔎 Buscar PV ou NF:", placeholder="Ex: 12345", key="exp_geral_busca").strip()

    with col_f3:
        if "DATA" in df.columns and df["DATA"].notna().any():
            min_dt = df["DATA"].min().date()
            max_dt = df["DATA"].max().date()
            periodo = st.date_input(
                "📅 Período:",
                value=(min_dt, max_dt),
                min_value=min_dt,
                max_value=max_dt,
                key="exp_geral_periodo",
            )
            if isinstance(periodo, tuple) and len(periodo) == 2:
                df = df[(df["DATA"].dt.date >= periodo[0]) & (df["DATA"].dt.date <= periodo[1])]

    if filial_sel != "Todas as Filiais":
        df = df[df["Filial_Norm"] == filial_sel]

    if busca_doc:
        mask_pv = df["PV_Norm"].astype(str).str.contains(busca_doc, case=False, na=False)
        mask_nf = df["NF_Norm"].astype(str).str.contains(busca_doc, case=False, na=False)
        df = df[mask_pv | mask_nf]

    # KPIs principais
    total_registros = len(df)
    total_pvs = df["PV_Norm"].replace("", pd.NA).dropna().nunique()
    total_nfs = df["NF_Norm"].replace("", pd.NA).dropna().nunique()
    total_filiais = df["Filial_Norm"].nunique()

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("📋 Total de Registros", f"{total_registros:,}".replace(",", "."))
    k2.metric("🧾 PVs Únicos", f"{total_pvs:,}".replace(",", "."))
    k3.metric("📄 NFs Únicas", f"{total_nfs:,}".replace(",", "."))
    k4.metric("🏢 Filiais Ativas", f"{total_filiais}")

    st.markdown("---")

    # Gráficos
    col_g1, col_g2 = st.columns(2)

    with col_g1:
        df_filial_agg = (
            df.groupby("Filial_Norm", as_index=False)
            .size()
            .rename(columns={"Filial_Norm": "Filial", "size": "Quantidade"})
            .sort_values("Quantidade", ascending=False)
        )
        fig_filial = px.bar(
            df_filial_agg,
            x="Filial",
            y="Quantidade",
            text_auto=True,
            title="Volume Expedido por Filial",
            color="Filial",
        )
        fig_filial.update_layout(showlegend=False, xaxis_title="", yaxis_title="Registros")
        st.plotly_chart(fig_filial, use_container_width=True)

    with col_g2:
        if "DATA" in df.columns and df["DATA"].notna().any():
            df_dia = (
                df.dropna(subset=["DATA"])
                .groupby(["DATA", "Filial_Norm"], as_index=False)
                .size()
                .rename(columns={"Filial_Norm": "Filial", "size": "Quantidade"})
                .sort_values("DATA")
            )
            fig_evol = px.line(
                df_dia,
                x="DATA",
                y="Quantidade",
                color="Filial",
                markers=True,
                title="Evolução Diária de Expedição por Filial",
            )
            fig_evol.update_layout(xaxis_title="Data", yaxis_title="Registros")
            st.plotly_chart(fig_evol, use_container_width=True)

    # Tabela detalhada
    st.markdown("### 📑 Detalhamento dos Registros")
    cols_ocultar = {"PV_Norm", "NF_Norm", "Filial_Norm", "Aba_Origem"}
    cols_exibir = ["Filial_Norm"] + [c for c in df.columns if c not in cols_ocultar]
    df_exibir = df[cols_exibir].rename(columns={"Filial_Norm": "Filial"})

    st.dataframe(df_exibir, use_container_width=True, hide_index=True)