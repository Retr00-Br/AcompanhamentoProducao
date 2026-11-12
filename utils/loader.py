import os
import pandas as pd
import streamlit as st


def get_data_filepath(filename: str) -> str:
    """Localiza o arquivo na pasta ./data/ ou na raiz do projeto."""
    path_data = os.path.join("./data/", filename)
    if os.path.exists(path_data):
        return path_data
    if os.path.exists(filename):
        return filename
    return ""


def get_frete_filepath() -> str:
    """Localiza dinamicamente a planilha de Custo de Fretes em ./data/ ou na raiz."""
    for folder in ["./data/", "."]:
        if os.path.exists(folder):
            for fname in os.listdir(folder):
                if "FRETE" in fname.upper() and fname.endswith(".xlsx") and not fname.startswith("~$"):
                    return os.path.join(folder, fname)
    return ""


@st.cache_data(ttl=60, show_spinner=False)
def load_dados_producao() -> pd.DataFrame:
    """Carrega a base oficial de Produção garantindo sincronia total com LimpezaDados."""
    filepath = get_data_filepath("DadosProducao.xlsx")
    if not filepath:
        return pd.DataFrame()

    try:
        excel = pd.ExcelFile(filepath)
        sheets = excel.sheet_names

        if "LimpezaDados" in sheets:
            df_limpeza = pd.read_excel(excel, sheet_name="LimpezaDados")
        elif "DadosBrutos" in sheets:
            df_b = pd.read_excel(excel, sheet_name="DadosBrutos")
            df_limpeza = df_b.groupby("DATA")["PV"].count().reset_index(name="Quantidade")
        else:
            return pd.DataFrame()

        df_limpeza["DATA"] = pd.to_datetime(df_limpeza["DATA"], errors="coerce").astype("datetime64[ns]")
        df_limpeza.rename(columns={"Quantidade": "Notas_Realizadas"}, inplace=True)
        df_limpeza["Quantidade"] = df_limpeza["Notas_Realizadas"]

        if "DadosBacklogXSaudavel" in sheets:
            df_bs = pd.read_excel(excel, sheet_name="DadosBacklogXSaudavel")
            df_bs["DATA"] = pd.to_datetime(df_bs["DATA"], errors="coerce").astype("datetime64[ns]")
            df_prod = pd.merge(df_limpeza, df_bs[["DATA", "Saudavel", "Backlog"]], on="DATA", how="outer")
        else:
            df_prod = df_limpeza.copy()
            df_prod["Saudavel"] = 0
            df_prod["Backlog"] = 0

        if "DadosBrutos" in sheets:
            df_brutos = pd.read_excel(excel, sheet_name="DadosBrutos")
            df_brutos["DATA"] = pd.to_datetime(df_brutos["DATA"], errors="coerce").astype("datetime64[ns]")
            col_sku = "SKU'S" if "SKU'S" in df_brutos.columns else ("SKUS" if "SKUS" in df_brutos.columns else df_brutos.columns[0])
            df_skus = df_brutos.groupby("DATA")[col_sku].count().reset_index(name="Total_SKUs")
            df_prod = pd.merge(df_prod, df_skus, on="DATA", how="outer")
        else:
            df_prod["Total_SKUs"] = df_prod["Quantidade"]

        for col in ["Quantidade", "Notas_Realizadas", "Saudavel", "Backlog", "Total_SKUs"]:
            df_prod[col] = pd.to_numeric(df_prod[col], errors="coerce").fillna(0)

        return df_prod.dropna(subset=["DATA"]).sort_values("DATA").reset_index(drop=True)

    except Exception as e:
        st.error(f"Erro ao carregar DadosProducao.xlsx: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=60, show_spinner=False)
def load_dados_romaneios() -> pd.DataFrame:
    """Carrega os volumes expedidos da aba DadosRomaneios."""
    filepath = get_data_filepath("DadosRomaneios.xlsx")
    if not filepath:
        return pd.DataFrame()

    try:
        excel = pd.ExcelFile(filepath)
        sheet_target = "DadosRomaneios" if "DadosRomaneios" in excel.sheet_names else excel.sheet_names[0]
        df_rom = pd.read_excel(excel, sheet_name=sheet_target)

        col_dt = "Dt. Romaneio" if "Dt. Romaneio" in df_rom.columns else df_rom.columns[0]
        col_qtd = "Qtd. Expedição" if "Qtd. Expedição" in df_rom.columns else df_rom.columns[1]

        df_rom.rename(columns={col_dt: "DATA", col_qtd: "Qtd. Expedição"}, inplace=True)
        df_rom["DATA"] = pd.to_datetime(df_rom["DATA"], errors="coerce").astype("datetime64[ns]")
        df_rom["Qtd. Expedição"] = pd.to_numeric(df_rom["Qtd. Expedição"], errors="coerce").fillna(0)

        return df_rom.dropna(subset=["DATA"]).sort_values("DATA").reset_index(drop=True)

    except Exception as e:
        st.error(f"Erro ao carregar DadosRomaneios.xlsx: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=60, show_spinner=False)
def load_dados_faturamento():
    """Carrega tanto o Faturamento Bruto por filial quanto o Faturamento Detalhado por Cliente."""
    filepath = get_data_filepath("DadosFaturamento.xlsx")
    if not filepath:
        return pd.DataFrame(), pd.DataFrame()

    try:
        excel = pd.ExcelFile(filepath)
        df_bruto = pd.read_excel(excel, sheet_name="FaturamentoBruto") if "FaturamentoBruto" in excel.sheet_names else pd.DataFrame()
        df_clientes = (
            pd.read_excel(excel, sheet_name="Faturamento por cliente")
            if "Faturamento por cliente" in excel.sheet_names
            else pd.DataFrame()
        )
        return df_clientes, df_bruto

    except Exception as e:
        st.error(f"Erro ao carregar DadosFaturamento.xlsx: {e}")
        return pd.DataFrame(), pd.DataFrame()


@st.cache_data(ttl=60, show_spinner=False)
def load_dados_frete() -> pd.DataFrame:
    """Lê TODAS as abas da planilha de Custo de Fretes (ex: '08-09', '10', etc.) e consolida os lançamentos."""
    filepath = get_frete_filepath()
    if not filepath:
        return pd.DataFrame()

    try:
        excel = pd.ExcelFile(filepath)
        dfs_abas = []

        for sheet in excel.sheet_names:
            df_sheet = pd.read_excel(excel, sheet_name=sheet)
            col_data = None
            col_valor = None

            for c in df_sheet.columns:
                c_up = str(c).strip().upper()
                if "EMISSÃO" in c_up or c_up == "DATA":
                    col_data = c
                elif c_up == "VL. FRETE" or c_up == "VALOR FRETE":
                    col_valor = c

            if col_data and col_valor:
                df_temp = df_sheet[[col_data, col_valor]].copy()
                df_temp.columns = ["DATA", "Valor Total Frete"]
                df_temp["DATA"] = pd.to_datetime(df_temp["DATA"], errors="coerce")
                df_temp["Valor Total Frete"] = pd.to_numeric(df_temp["Valor Total Frete"], errors="coerce").fillna(0.0)
                df_temp = df_temp.dropna(subset=["DATA"])
                dfs_abas.append(df_temp)

        if not dfs_abas:
            return pd.DataFrame()

        df_frete_total = pd.concat(dfs_abas, ignore_index=True)
        df_frete_total["DATA"] = df_frete_total["DATA"].astype("datetime64[ns]")
        return df_frete_total.sort_values("DATA").reset_index(drop=True)

    except Exception as e:
        st.error(f"Erro ao ler abas da planilha de frete: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=60, show_spinner=False)
def load_resumo_terceiros_MNOP() -> pd.DataFrame:
    """Consolida o resumo lateral por transportadora terceirizada de TODAS as abas da planilha de frete."""
    filepath = get_frete_filepath()
    if not filepath:
        return pd.DataFrame()

    try:
        excel = pd.ExcelFile(filepath)
        dfs_mnop = []

        for sheet in excel.sheet_names:
            df_s = pd.read_excel(excel, sheet_name=sheet)
            if "Rótulos de Linha" in df_s.columns:
                col_nf = (
                    "Soma de Vlr_Nota_Fiscal"
                    if "Soma de Vlr_Nota_Fiscal" in df_s.columns
                    else ("Vlr. Nota Fiscal" if "Vlr. Nota Fiscal" in df_s.columns else None)
                )
                col_fr = (
                    "Soma de VL. FRETE"
                    if "Soma de VL. FRETE" in df_s.columns
                    else ("VL. FRETE.1" if "VL. FRETE.1" in df_s.columns else None)
                )

                if col_nf and col_fr:
                    df_m = df_s[["Rótulos de Linha", col_nf, col_fr]].dropna(subset=["Rótulos de Linha"]).copy()
                    df_m.columns = ["Transportadora", "Valor_NF", "Valor_Frete"]
                    df_m["Transportadora"] = df_m["Transportadora"].astype(str).str.strip().str.upper()
                    df_m = df_m[~df_m["Transportadora"].str.contains("TOTAL")]
                    df_m["Valor_NF"] = pd.to_numeric(df_m["Valor_NF"], errors="coerce").fillna(0.0)
                    df_m["Valor_Frete"] = pd.to_numeric(df_m["Valor_Frete"], errors="coerce").fillna(0.0)
                    dfs_mnop.append(df_m)

        if not dfs_mnop:
            return pd.DataFrame()

        df_consolidado = (
            pd.concat(dfs_mnop, ignore_index=True)
            .groupby("Transportadora", as_index=False)[["Valor_NF", "Valor_Frete"]]
            .sum()
        )
        df_consolidado["Pct_Frete"] = (df_consolidado["Valor_Frete"] / df_consolidado["Valor_NF"]).fillna(0.0)
        return df_consolidado.sort_values("Valor_Frete", ascending=False).reset_index(drop=True)

    except Exception as e:
        st.error(f"Erro ao consolidar resumo de terceiros MNOP: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=60, show_spinner=False)
def load_treated_data_cached():
    """Carrega todas as bases unificadas e cacheadas."""
    df_prod = load_dados_producao()
    df_rom = load_dados_romaneios()
    df_fat_clientes, df_fat_bruto = load_dados_faturamento()
    df_frete = load_dados_frete()
    return df_prod, df_rom, df_fat_clientes, df_fat_bruto, df_frete