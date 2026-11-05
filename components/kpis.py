import streamlit as st
import pandas as pd


def render_kpis_gerais(df_filtrado: pd.DataFrame):
    st.markdown("### 📊 Indicadores Gerais de Produção")

    if df_filtrado is None or df_filtrado.empty:
        st.info("Sem dados para o período selecionado.")
        return

    total_pvs = int(df_filtrado.get("Total_PVs", pd.Series([0])).sum())
    saudavel = int(df_filtrado.get("Saudavel", pd.Series([0])).sum())
    backlog = int(df_filtrado.get("Backlog", pd.Series([0])).sum())
    total_skus = int(df_filtrado.get("Total_SKUs", pd.Series([0])).sum())

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📄 Total PVs", f"{total_pvs}")
    c2.metric("✅ Saudável", f"{saudavel}")
    c3.metric("⚠️ Backlog", f"{backlog}")
    c4.metric("📦 Total SKUs/Linhas", f"{total_skus}")


def render_kpis_medias(df_filtrado: pd.DataFrame, unidade_selecionada: str):
    st.markdown("### 🎯 Médias Diárias da Operação")

    if df_filtrado is None or df_filtrado.empty:
        return

    df_dias_validos = df_filtrado[df_filtrado.get("Total_PVs", 0) > 0].copy()
    dias_count = len(df_dias_validos) if len(df_dias_validos) > 0 else 1

    saudavel_sum = df_filtrado.get("Saudavel", pd.Series([0])).sum()
    backlog_sum = df_filtrado.get("Backlog", pd.Series([0])).sum()
    skus_sum = df_filtrado.get("Total_SKUs", pd.Series([0])).sum()

    media_saudavel = saudavel_sum / dias_count
    media_backlog = backlog_sum / dias_count
    media_skus = skus_sum / dias_count

    col_fat = f"{unidade_selecionada}_Fat"
    val_fat = df_filtrado[col_fat].sum() if col_fat in df_filtrado.columns else df_filtrado.get("Todas as Unidades (Geral)_Fat", pd.Series([0])).sum()
    media_fat = val_fat / dias_count

    media_expedicao = df_filtrado.get("Total_Expedidos", pd.Series([0])).sum() / dias_count

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("📈 Média Saudável/Dia", f"{media_saudavel:.1f}")
    c2.metric("⚠️ Média Backlog/Dia", f"{media_backlog:.1f}")
    c3.metric("📦 Média SKUs/Linhas/Dia", f"{media_skus:.1f}")
    c4.metric("💵 Média Faturada/Dia", f"R$ {media_fat:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    c5.metric("🚚 Média de Expedição", f"{media_expedicao:.1f} vol.")