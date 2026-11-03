import os
import pandas as pd
import streamlit as st


@st.cache_data(ttl=1800, show_spinner=False)
def load_treated_data_cached():
    """Lê as abas tratadas e extrai a soma real de SKUs sem travar o frontend."""
    data_dir = "./data/"

    def get_path(filename):
        p = os.path.join(data_dir, filename)
        return p if os.path.exists(p) else (filename if os.path.exists(filename) else None)

    # 1. Produção: LimpezaDados + DadosBacklogXSaudavel
    path_prod = get_path("DadosProducao.xlsx")
    if path_prod:
        try:
            df_limpeza = pd.read_excel(path_prod, sheet_name="LimpezaDados")
            df_status = pd.read_excel(path_prod, sheet_name="DadosBacklogXSaudavel")

            df_limpeza["DATA"] = pd.to_datetime(df_limpeza["DATA"], errors="coerce")
            df_status["DATA"] = pd.to_datetime(df_status["DATA"], errors="coerce")

            df_prod_base = pd.merge(df_limpeza, df_status, on="DATA", how="outer")

            # Leitura isolada apenas da coluna SKU'S
            df_brutos = pd.read_excel(path_prod, sheet_name="DadosBrutos", usecols=["DATA", "SKU'S"])
            df_brutos["DATA"] = pd.to_datetime(df_brutos["DATA"], errors="coerce")
            df_brutos["SKU'S"] = pd.to_numeric(df_brutos["SKU'S"], errors="coerce").fillna(0)

            df_sku_agg = df_brutos.groupby("DATA")["SKU'S"].sum().reset_index(name="Total_SKUs")
            df_prod_tratado = pd.merge(df_prod_base, df_sku_agg, on="DATA", how="left").fillna({"Total_SKUs": 0})
        except Exception:
            df_prod_tratado = pd.DataFrame(columns=["DATA", "Quantidade", "Saudavel", "Backlog", "Total_SKUs"])
    else:
        df_prod_tratado = pd.DataFrame(columns=["DATA", "Quantidade", "Saudavel", "Backlog", "Total_SKUs"])

    # 2. Romaneios
    path_rom = get_path("DadosRomaneios.xlsx")
    if path_rom:
        try:
            df_rom_tratado = pd.read_excel(path_rom, sheet_name="DadosRomaneios")
            df_rom_tratado["DATA"] = pd.to_datetime(df_rom_tratado["Dt. Romaneio"], errors="coerce")
        except Exception:
            df_rom_tratado = pd.DataFrame(columns=["DATA", "Qtd. Expedição"])
    else:
        df_rom_tratado = pd.DataFrame(columns=["DATA", "Qtd. Expedição"])

    # 3. Faturamento
    path_fat = get_path("DadosFaturamento.xlsx")
    if path_fat:
        try:
            df_fat_detalhado = pd.read_excel(path_fat, sheet_name="Faturamento por cliente")
            df_fat_bruto_raw = pd.read_excel(path_fat, sheet_name="FaturamentoBruto", header=None)
        except Exception:
            df_fat_detalhado = pd.DataFrame()
            df_fat_bruto_raw = pd.DataFrame()
    else:
        df_fat_detalhado = pd.DataFrame()
        df_fat_bruto_raw = pd.DataFrame()

    # 4. Fretes Terceirizados
    path_frete = get_path("SOLICITACAO TERCEIROS.xlsx")
    if path_frete:
        try:
            df_frete_tratado = pd.read_excel(path_frete, sheet_name="26")
        except Exception:
            df_frete_tratado = pd.DataFrame()

        if not df_frete_tratado.empty and "Data da solicitação" in df_frete_tratado.columns:
            df_frete_tratado["DATA"] = pd.to_datetime(df_frete_tratado["Data da solicitação"], errors="coerce")
            df_frete_tratado["Valor Total Frete"] = pd.to_numeric(
                df_frete_tratado["Valor Total Frete"], errors="coerce"
            ).fillna(0.0)
            df_frete_tratado["Valor Total NF"] = pd.to_numeric(
                df_frete_tratado["Valor Total NF"], errors="coerce"
            ).fillna(0.0)
        else:
            df_frete_tratado = pd.DataFrame(columns=["DATA", "Valor Total Frete", "Valor Total NF"])
    else:
        df_frete_tratado = pd.DataFrame(columns=["DATA", "Valor Total Frete", "Valor Total NF"])

    return (
        df_prod_tratado,
        df_rom_tratado,
        df_fat_detalhado,
        df_fat_bruto_raw,
        df_frete_tratado,
    )