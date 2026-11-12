import pandas as pd
import streamlit as st


def _fmt_brl(val: float) -> str:
    return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def render_kpis_gerais(df_filtrado: pd.DataFrame):
    """Renderiza os KPIs superiores de Faturamento e Devoluções."""
    if df_filtrado is None or df_filtrado.empty:
        return

    fat_total = df_filtrado.get("Todas as Unidades (Geral)_Fat", pd.Series([0.0])).sum()
    dev_total = df_filtrado.get("Todas as Unidades (Geral)_Dev", pd.Series([0.0])).sum()
    fat_liquido = fat_total - dev_total
    pct_dev = (dev_total / fat_total * 100) if fat_total > 0 else 0.0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 Faturamento Bruto Geral", _fmt_brl(fat_total))
    c2.metric("📉 Total Devoluções", _fmt_brl(dev_total))
    c3.metric("💵 Faturamento Líquido", _fmt_brl(fat_liquido))
    c4.metric("⚠️ % Índice de Devolução", f"{pct_dev:.2f}%")


def render_kpis_medias(df_filtrado: pd.DataFrame, unidade_selecionada: str):
    """Renderiza os KPIs operacionais da aba de Produção & Expedição."""
    if df_filtrado is None or df_filtrado.empty:
        return

    total_notas = int(df_filtrado.get("Notas_Realizadas", pd.Series([0])).sum())
    total_exp = int(df_filtrado.get("Total_Expedidos", pd.Series([0])).sum())
    total_saudavel = int(df_filtrado.get("Saudavel", pd.Series([0])).sum())
    total_backlog = int(df_filtrado.get("Backlog", pd.Series([0])).sum())

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📋 Notas Realizadas (PVs)", f"{total_notas:,}".replace(",", "."))
    c2.metric("🚚 Volume Expedido", f"{total_exp:,}".replace(",", "."))
    c3.metric("✅ Notas Saudáveis", f"{total_saudavel:,}".replace(",", "."))
    c4.metric("⏳ Notas em Backlog", f"{total_backlog:,}".replace(",", "."))