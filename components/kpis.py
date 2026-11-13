import pandas as pd
import streamlit as st


def _fmt_brl(val: float) -> str:
    sinal = "-" if val < 0 else ""
    return f"{sinal}R$ {abs(val):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def render_kpis_gerais(df_filtrado: pd.DataFrame, unidade_selecionada: str = "Todas as Unidades (Geral)"):
    if df_filtrado is None or df_filtrado.empty:
        return

    col_fat = f"{unidade_selecionada}_Fat"
    col_dev = f"{unidade_selecionada}_Dev"

    if col_fat not in df_filtrado.columns:
        col_fat = "Todas as Unidades (Geral)_Fat"
    if col_dev not in df_filtrado.columns:
        col_dev = "Todas as Unidades (Geral)_Dev"

    valor_planilha_fat = df_filtrado[col_fat].sum() if col_fat in df_filtrado.columns else 0.0
    dev_raw = df_filtrado[col_dev].sum() if col_dev in df_filtrado.columns else 0.0
    dev_abs = abs(dev_raw)

    # Na aba FaturamentoBruto, a coluna TOT (Todas as Unidades (Geral)_Fat) já é o valor líquido (Bruto - Devoluções),
    # enquanto as colunas individuais das filiais (0101, 0102, 0103, 0104) trazem o faturamento bruto da filial.
    if unidade_selecionada == "Todas as Unidades (Geral)":
        fat_liquido = valor_planilha_fat
        fat_bruto = fat_liquido + dev_abs
    else:
        fat_bruto = valor_planilha_fat
        fat_liquido = fat_bruto - dev_abs

    dev_exibicao = -dev_abs if dev_abs > 0 else 0.0

    dias_com_fat = int((df_filtrado[col_fat] > 0).sum()) if col_fat in df_filtrado.columns else len(df_filtrado)
    media_fat_dia = (fat_liquido / dias_com_fat) if dias_com_fat > 0 else 0.0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 Faturamento Bruto", _fmt_brl(fat_bruto))
    c2.metric("↩️ Devoluções Totais", _fmt_brl(dev_exibicao))
    c3.metric("💵 Faturamento Líquido", _fmt_brl(fat_liquido))
    c4.metric("📊 Média Diária Faturamento", _fmt_brl(media_fat_dia), delta=f"{dias_com_fat} dias úteis", delta_color="off")


def render_kpis_medias(df_filtrado: pd.DataFrame, unidade_selecionada: str = "Todas as Unidades (Geral)"):
    if df_filtrado is None or df_filtrado.empty:
        return

    mask_op = (
        (df_filtrado.get("Notas_Realizadas", 0) > 0)
        | (df_filtrado.get("Saudavel", 0) > 0)
        | (df_filtrado.get("Backlog", 0) > 0)
        | (df_filtrado.get("Total_Expedidos", 0) > 0)
    )
    df_op = df_filtrado[mask_op].copy()
    if df_op.empty:
        df_op = df_filtrado.copy()

    dias_op = max(len(df_op), 1)
    dias_exp = max(int((df_op["Total_Expedidos"] > 0).sum()), 1) if "Total_Expedidos" in df_op.columns else dias_op

    total_notas = df_op["Notas_Realizadas"].sum() if "Notas_Realizadas" in df_op.columns else 0.0
    total_saudavel = df_op["Saudavel"].sum() if "Saudavel" in df_op.columns else 0.0
    total_backlog = df_op["Backlog"].sum() if "Backlog" in df_op.columns else 0.0
    total_skus = df_op["Total_SKUs"].sum() if "Total_SKUs" in df_op.columns else 0.0
    total_expedidos = df_op["Total_Expedidos"].sum() if "Total_Expedidos" in df_op.columns else 0.0

    media_notas = total_notas / dias_op
    media_saudavel = total_saudavel / dias_op
    media_backlog = total_backlog / dias_op
    media_skus = total_skus / dias_op
    media_expedicao = total_expedidos / dias_exp

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric(
        "📦 Média Notas Realizadas / Dia",
        f"{media_notas:,.1f}".replace(",", "."),
        delta=f"Total: {int(total_notas):,}".replace(",", "."),
        delta_color="off",
    )
    c2.metric(
        "🟢 Média Notas Saudáveis / Dia",
        f"{media_saudavel:,.1f}".replace(",", "."),
        delta=f"Total: {int(total_saudavel):,}".replace(",", "."),
        delta_color="normal",
    )
    c3.metric(
        "🔴 Média Backlog / Dia",
        f"{media_backlog:,.1f}".replace(",", "."),
        delta=f"Total: {int(total_backlog):,}".replace(",", "."),
        delta_color="inverse",
    )
    c4.metric(
        "🚚 Média Expedição / Dia",
        f"{media_expedicao:,.1f}".replace(",", "."),
        delta=f"Total: {int(total_expedidos):,} ({dias_exp} dias)".replace(",", "."),
        delta_color="off",
    )
    c5.metric(
        "🏷️ Média SKUs Separados / Dia",
        f"{media_skus:,.1f}".replace(",", "."),
        delta=f"Total: {int(total_skus):,}".replace(",", "."),
        delta_color="off",
    )