import os
import pandas as pd
import streamlit as st


@st.cache_data(ttl=1800, show_spinner=False)
def load_treated_data_cached():
    """Lê todas as planilhas do diretório ./data/ incluindo dados de frete e SKUs reais."""
    data_dir = "./data/"

    def get_path(filename):
        p = os.path.join(data_dir, filename)
        return p if os.path.exists(p) else (filename if os.path.exists(filename) else None)

    # 1. Produção: LimpezaDados + DadosBacklogXSaudavel + SKUs reais
    path_prod = get_path("DadosProducao.xlsx")
    if path_prod:
        try:
            df_limpeza = pd.read_excel(path_prod, sheet_name="LimpezaDados")
            df_status = pd.read_excel(path_prod, sheet_name="DadosBacklogXSaudavel")

            df_limpeza["DATA"] = pd.to_datetime(df_limpeza["DATA"], errors="coerce")
            df_status["DATA"] = pd.to_datetime(df_status["DATA"], errors="coerce")

            df_prod_base = pd.merge(df_limpeza, df_status, on="DATA", how="outer")

            df_brutos = pd.read_excel(path_prod, sheet_name="DadosBrutos")
            col_sku = "SKU'S" if "SKU'S" in df_brutos.columns else ("SKU" if "SKU" in df_brutos.columns else None)

            if col_sku:
                df_brutos["DATA"] = pd.to_datetime(df_brutos["DATA"], errors="coerce")
                df_brutos[col_sku] = pd.to_numeric(df_brutos[col_sku], errors="coerce").fillna(0)
                df_sku_agg = df_brutos.groupby("DATA")[col_sku].sum().reset_index(name="Total_SKUs")
                df_prod_tratado = pd.merge(df_prod_base, df_sku_agg, on="DATA", how="left").fillna({"Total_SKUs": 0})
            else:
                df_prod_base["Total_SKUs"] = 0
                df_prod_tratado = df_prod_base
        except Exception:
            df_prod_tratado = pd.DataFrame(columns=["DATA", "Quantidade", "Saudavel", "Backlog", "Total_SKUs"])
    else:
        df_prod_tratado = pd.DataFrame(columns=["DATA", "Quantidade", "Saudavel", "Backlog", "Total_SKUs"])

    # 2. Romaneios (Expedições)
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

    # 4. Fretes Terceirizados - Nova Planilha (Colunas C, H, D)
    path_frete = (
        get_path("RELAÇÃO CUSTO FRETES_2026-08_09_2.xlsx")
        or get_path("RELAÇÃO CUSTO FRETES_2026-08_09.xlsx")
        or get_path("SOLICITACAO TERCEIROS.xlsx")
    )
    if path_frete:
        try:
            df_frete_raw = pd.read_excel(path_frete, sheet_name=0)

            if "EMISSÃO CTE/NFE" in df_frete_raw.columns and "VL. FRETE" in df_frete_raw.columns:
                df_frete_tratado = df_frete_raw.copy()
                df_frete_tratado["DATA"] = pd.to_datetime(df_frete_tratado["EMISSÃO CTE/NFE"], errors="coerce")
                df_frete_tratado["Valor Total Frete"] = pd.to_numeric(
                    df_frete_tratado["VL. FRETE"], errors="coerce"
                ).fillna(0.0)
                df_frete_tratado["TRANSPORTADORA"] = df_frete_tratado["TRANSPORTADORA"].fillna("OUTROS").astype(str)
            else:
                df_frete_tratado = df_frete_raw.copy()
                df_frete_tratado["DATA"] = pd.to_datetime(df_frete_tratado["Data da solicitação"], errors="coerce")
                df_frete_tratado["Valor Total Frete"] = pd.to_numeric(
                    df_frete_tratado["Valor Total Frete"], errors="coerce"
                ).fillna(0.0)
                df_frete_tratado["TRANSPORTADORA"] = "GERAL"
        except Exception:
            df_frete_tratado = pd.DataFrame(columns=["DATA", "Valor Total Frete", "TRANSPORTADORA"])
    else:
        df_frete_tratado = pd.DataFrame(columns=["DATA", "Valor Total Frete", "TRANSPORTADORA"])

    return (
        df_prod_tratado,
        df_rom_tratado,
        df_fat_detalhado,
        df_fat_bruto_raw,
        df_frete_tratado,
    )


@st.cache_data(ttl=1800, show_spinner=False)
def load_resumo_terceiros_MNOP():
    """Lê diretamente a tabela dinâmica das Colunas M, N, O e P da planilha de Fretes."""
    data_dir = "./data/"

    def get_path(filename):
        p = os.path.join(data_dir, filename)
        return p if os.path.exists(p) else (filename if os.path.exists(filename) else None)

    path_frete = (
        get_path("RELAÇÃO CUSTO FRETES_2026-08_09_2.xlsx")
        or get_path("RELAÇÃO CUSTO FRETES_2026-08_09.xlsx")
        or get_path("SOLICITACAO TERCEIROS.xlsx")
    )

    if not path_frete:
        return pd.DataFrame()

    try:
        df_raw = pd.read_excel(path_frete, sheet_name=0)
        df_mnop = df_raw.iloc[:, 12:16].dropna(subset=[df_raw.columns[12]]).copy()
        df_mnop.columns = ["Transportadora", "Valor_NF", "Valor_Frete", "Pct_Frete"]

        df_mnop["Valor_NF"] = pd.to_numeric(df_mnop["Valor_NF"], errors="coerce").fillna(0.0)
        df_mnop["Valor_Frete"] = pd.to_numeric(df_mnop["Valor_Frete"], errors="coerce").fillna(0.0)
        df_mnop["Pct_Frete"] = pd.to_numeric(df_mnop["Pct_Frete"], errors="coerce").fillna(0.0)

        return df_mnop
    except Exception:
        return pd.DataFrame()