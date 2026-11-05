import pandas as pd
import streamlit as st


def render_kpis_gerais(df_filtrado: pd.DataFrame):
    st.markdown("### 📊 Indicadores Gerais de Produção")
    
    total_pvs = int(df_filtrado["Total_PVs"].sum()) if "Total_PVs" in df_filtrado.columns else 0
    
    col_saudavel = "Saudavel" if "Saudavel" in df_filtrado.columns else "SAUDAVEL"
    col_backlog = "Backlog" if "Backlog" in df_filtrado.columns else "BACKLOG"
    
    saudavel = int(df_filtrado[col_saudavel].sum()) if col_saudavel in df_filtrado.columns else 0
    backlog = int(df_filtrado[col_backlog].sum()) if col_backlog in df_filtrado.columns else 0
    total_skus = int(df_filtrado["Total_SKUs"].sum()) if "Total_SKUs" in df_filtrado.columns else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📄 Total PVs", f"{total_pvs}")
    c2.metric("✅ Saudável", f"{saudavel}")
    c3.metric("⚠️ Backlog", f"{backlog}")
    c4.metric("📦 Total SKUs/Linhas", f"{total_skus}")


def render_kpis_medias(df_filtrado: pd.DataFrame, unidade_selecionada: str):
    st.markdown("### 🎯 Médias Diárias da Operação")
    if df_filtrado.empty:
        return

    col_fat_ativa = f"{unidade_selecionada}_Fat"
    fat_total = float(df_filtrado[col_fat_ativa].sum()) if col_fat_ativa in df_filtrado.columns else 0.0
    dias_com_fat = len(df_filtrado[df_filtrado[col_fat_ativa] > 0])
    media_fat_diaria = fat_total / (dias_com_fat if dias_com_fat > 0 else 1)

    media_saudavel = float(df_filtrado["SAUDAVEL"].mean())
    media_backlog = float(df_filtrado["BACKLOG"].mean())
    media_skus = float(df_filtrado["Total_SKUs"].mean())

    df_exp = df_filtrado[df_filtrado["Total_Expedidos"] > 0]
    if df_exp.empty:
        df_exp = df_filtrado
    media_expedidos = float(df_exp["Total_Expedidos"].mean())

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
        help="Média diária de volumes expedidos considerando apenas dias com operação de romaneio.",
    )