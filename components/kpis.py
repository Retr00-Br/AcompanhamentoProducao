import pandas as pd
import streamlit as st


FILIAL_COD_MAP = {
    "0101 - Matriz": "101",
    "0102 - Filial RJ": "102",
    "0103 - Filial CP": "103",
    "0104 - Filial SBC": "104",
}


def _fmt_brl(val: float) -> str:
    sinal = "-" if val < 0 else ""
    return f"{sinal}R$ {abs(val):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def render_kpis_gerais(
    df_filtrado: pd.DataFrame,
    unidade_selecionada: str = "Todas as Unidades (Geral)",
    df_fat_detalhado: pd.DataFrame = None,
):
    if df_filtrado is None or df_filtrado.empty:
        return

    col_fat = f"{unidade_selecionada}_Fat"
    col_dev = f"{unidade_selecionada}_Dev"

    if col_fat not in df_filtrado.columns:
        col_fat = "Todas as Unidades (Geral)_Fat"
    if col_dev not in df_filtrado.columns:
        col_dev = "Todas as Unidades (Geral)_Dev"

    dev_abs = abs(df_filtrado[col_dev].sum()) if col_dev in df_filtrado.columns else 0.0
    dev_exibicao = -dev_abs if dev_abs > 0 else 0.0

    if unidade_selecionada == "Todas as Unidades (Geral)" and "Todas as Unidades (Geral)_Liq" in df_filtrado.columns:
        fat_bruto = df_filtrado["Todas as Unidades (Geral)_Fat"].sum()
        fat_liquido = df_filtrado["Todas as Unidades (Geral)_Liq"].sum()
        col_ref_dia = "Todas as Unidades (Geral)_Liq"
    else:
        val_fat = df_filtrado[col_fat].sum() if col_fat in df_filtrado.columns else 0.0
        if unidade_selecionada == "Todas as Unidades (Geral)":
            fat_liquido = val_fat
            fat_bruto = fat_liquido + dev_abs
        else:
            fat_bruto = val_fat
            fat_liquido = fat_bruto - dev_abs
        col_ref_dia = col_fat

    dias_com_fat = int((df_filtrado[col_fat] > 0).sum()) if col_fat in df_filtrado.columns else len(df_filtrado)
    media_fat_dia = (fat_liquido / dias_com_fat) if dias_com_fat > 0 else 0.0

    # Linha 1: KPIs Monetários Principais
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 Faturamento Bruto", _fmt_brl(fat_bruto))
    c2.metric("↩️ Devoluções Totais", _fmt_brl(dev_exibicao))
    c3.metric("💵 Faturamento Líquido", _fmt_brl(fat_liquido))
    c4.metric("📊 Média Diária Faturamento", _fmt_brl(media_fat_dia), delta=f"{dias_com_fat} dias úteis", delta_color="off")

    # Linha 2: KPIs de Recordes Diários e Clientes no Período Selecionado
    df_dias_ativos = df_filtrado[df_filtrado[col_fat] > 0].copy()
    if not df_dias_ativos.empty:
        idx_max_d = df_dias_ativos[col_ref_dia].idxmax()
        idx_min_d = df_dias_ativos[col_ref_dia].idxmin()
        row_max_d = df_dias_ativos.loc[idx_max_d]
        row_min_d = df_dias_ativos.loc[idx_min_d]

        maior_dia_str = pd.to_datetime(row_max_d["DATA"]).strftime("%d/%m/%Y")
        maior_dia_val = _fmt_brl(float(row_max_d[col_ref_dia]))

        menor_dia_str = pd.to_datetime(row_min_d["DATA"]).strftime("%d/%m/%Y")
        menor_dia_val = _fmt_brl(float(row_min_d[col_ref_dia]))
    else:
        maior_dia_str, maior_dia_val = "-", "R$ 0,00"
        menor_dia_str, menor_dia_val = "-", "R$ 0,00"

    top_cli_nome, top_cli_val = "-", "R$ 0,00"
    bot_cli_nome, bot_cli_val = "-", "R$ 0,00"

    if df_fat_detalhado is not None and not df_fat_detalhado.empty and "Cliente" in df_fat_detalhado.columns:
        df_c = df_fat_detalhado.copy()
        df_c.columns = [str(c).strip() for c in df_c.columns]
        col_val_c = next((c for c in df_c.columns if "FATUR" in c.upper() or "VALOR" in c.upper()), df_c.columns[-1])
        df_c[col_val_c] = pd.to_numeric(df_c[col_val_c], errors="coerce").fillna(0.0)

        # Filtra pela competência (YYYY-MM) dos dias selecionados no calendário
        meses_sel = pd.to_datetime(df_filtrado["DATA"]).dt.strftime("%Y-%m").unique().tolist()
        if "Mês" in df_c.columns and meses_sel:
            df_c["Mes_Str"] = pd.to_datetime(df_c["Mês"], errors="coerce").dt.strftime("%Y-%m")
            df_c = df_c[df_c["Mes_Str"].isin(meses_sel)].copy()

        # Filtra pela unidade/filial selecionada
        if unidade_selecionada in FILIAL_COD_MAP and "Filial" in df_c.columns:
            cod_alvo = FILIAL_COD_MAP[unidade_selecionada]
            df_c["Filial_Clean"] = (
                df_c["Filial"].astype(str).str.replace(".0", "", regex=False).str.strip().str.lstrip("0")
            )
            df_c = df_c[df_c["Filial_Clean"] == cod_alvo].copy()

        df_c["Cliente"] = df_c["Cliente"].fillna("NÃO INFORMADO").astype(str).str.strip().str.upper()
        df_c_grp = df_c.groupby("Cliente", as_index=False)[col_val_c].sum()
        df_c_grp = df_c_grp[df_c_grp[col_val_c] != 0].sort_values(col_val_c, ascending=False).reset_index(drop=True)

        if not df_c_grp.empty:
            top_cli_nome = str(df_c_grp.iloc[0]["Cliente"])[:24]
            top_cli_val = _fmt_brl(float(df_c_grp.iloc[0][col_val_c]))

            bot_cli_nome = str(df_c_grp.iloc[-1]["Cliente"])[:24]
            bot_cli_val = _fmt_brl(float(df_c_grp.iloc[-1][col_val_c]))

    st.markdown("<div style='margin-top: 6px;'></div>", unsafe_allow_html=True)
    e1, e2, e3, e4 = st.columns(4)
    e1.metric("📈 Dia c/ Maior Faturamento", maior_dia_str, delta=maior_dia_val, delta_color="normal")
    e2.metric("📉 Dia c/ Menor Faturamento", menor_dia_str, delta=menor_dia_val, delta_color="inverse")
    e3.metric("🏆 Cliente c/ Maiores Compras", top_cli_nome, delta=top_cli_val, delta_color="normal")
    e4.metric("🔻 Cliente c/ Menores Compras", bot_cli_nome, delta=bot_cli_val, delta_color="inverse")


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

    # Linha 1: Médias Diárias
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

    # Linha 2: Recordes no Período (Maior/Menor Expedição e Maior/Menor Produção Realizada)
    df_exp_ativos = df_op[df_op["Total_Expedidos"] > 0].copy() if "Total_Expedidos" in df_op.columns else pd.DataFrame()
    if not df_exp_ativos.empty:
        r_max_exp = df_exp_ativos.loc[df_exp_ativos["Total_Expedidos"].idxmax()]
        r_min_exp = df_exp_ativos.loc[df_exp_ativos["Total_Expedidos"].idxmin()]
        max_exp_dia = pd.to_datetime(r_max_exp["DATA"]).strftime("%d/%m/%Y")
        max_exp_val = f"{int(r_max_exp['Total_Expedidos']):,} NFs (Média: {media_expedicao:,.1f}/dia)".replace(",", ".")
        min_exp_dia = pd.to_datetime(r_min_exp["DATA"]).strftime("%d/%m/%Y")
        min_exp_val = f"{int(r_min_exp['Total_Expedidos']):,} NFs".replace(",", ".")
    else:
        max_exp_dia, max_exp_val = "-", "0 NFs"
        min_exp_dia, min_exp_val = "-", "0 NFs"

    df_prod_ativos = df_op[df_op["Notas_Realizadas"] > 0].copy() if "Notas_Realizadas" in df_op.columns else pd.DataFrame()
    if not df_prod_ativos.empty:
        r_max_prod = df_prod_ativos.loc[df_prod_ativos["Notas_Realizadas"].idxmax()]
        r_min_prod = df_prod_ativos.loc[df_prod_ativos["Notas_Realizadas"].idxmin()]
        max_prod_dia = pd.to_datetime(r_max_prod["DATA"]).strftime("%d/%m/%Y")
        max_prod_val = f"{int(r_max_prod['Notas_Realizadas']):,} notas".replace(",", ".")
        min_prod_dia = pd.to_datetime(r_min_prod["DATA"]).strftime("%d/%m/%Y")
        min_prod_val = f"{int(r_min_prod['Notas_Realizadas']):,} notas".replace(",", ".")
    else:
        max_prod_dia, max_prod_val = "-", "0 notas"
        min_prod_dia, min_prod_val = "-", "0 notas"

    st.markdown("<div style='margin-top: 6px;'></div>", unsafe_allow_html=True)
    r1, r2, r3, r4 = st.columns(4)
    r1.metric("🚀 Dia c/ Maior Expedição", max_exp_dia, delta=max_exp_val, delta_color="normal")
    r2.metric("📉 Dia c/ Menor Expedição", min_exp_dia, delta=min_exp_val, delta_color="inverse")
    r3.metric("🏭 Maior Dia de Produção", max_prod_dia, delta=max_prod_val, delta_color="normal")
    r4.metric("🔻 Menor Dia de Produção", min_prod_dia, delta=min_prod_val, delta_color="inverse")