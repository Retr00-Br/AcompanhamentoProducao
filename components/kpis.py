import pandas as pd
import streamlit as st


def render_kpis_gerais(df_filtrado: pd.DataFrame):
    st.markdown("### 📊 Indicadores Gerais de Produção")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("📄 Total PVs", int(df_filtrado["Total_PVs"].sum()))
    k2.metric("✅ Saudável", int(df_filtrado["SAUDAVEL"].sum()))
    k3.metric("⚠️ Backlog", int(df_filtrado["BACKLOG"].sum()))
    k4.metric("📦 Total SKUs/Linhas", int(df_filtrado["Total_SKUs"].sum()))
    st.divider()


def render_kpis_medias(df_filtrado: pd.DataFrame, unidade_selecionada: str):
    st.markdown("### 🎯 Médias Diárias da Operação")
    if df_filtrado.empty:
        return

    col_fat_ativa = f"{unidade_selecionada}_Fat"
    fat_total = df_filtrado[col_fat_ativa].sum() if col_fat_ativa in df_filtrado.columns else 0.0
    dias_com_fat = len(df_filtrado[df_filtrado[col_fat_ativa] > 0])
    media_fat_diaria = fat_total / (dias_com_fat if dias_com_fat > 0 else 1)

    media_saudavel = df_filtrado["SAUDAVEL"].mean()
    media_backlog = df_filtrado["BACKLOG"].mean()
    media_skus = df_filtrado["Total_SKUs"].mean()

    # Média isolada de expedição (sem preditivos)
    df_exp = df_filtrado[df_filtrado["Total_Expedidos"] > 0]
    if df_exp.empty:
        df_exp = df_filtrado
    media_expedidos = df_exp["Total_Expedidos"].mean()

    pm1, pm2, pm3, pm4, pm5 = st.columns(5)
    pm1.metric("📈 Média Saudável/Dia", f"{media_saudavel:.1f}")
    pm2.metric("⚠️ Média Backlog/Dia", f"{media_backlog:.1f}")
    pm3.metric("📦 Média SKUs/Linhas/Dia", f"{media_skus:.1f}")
    pm4.metric(
        "💵 Média Faturada/Dia",
        f"R$ {media_fat_diaria:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
    )
    pm5.metric(
        "🚚 Média de Expedição",
        f"{media_expedidos:.1f} vol.",
        help="Média diária de volumes expedidos considerando apenas dias com operação de romaneio."
    )