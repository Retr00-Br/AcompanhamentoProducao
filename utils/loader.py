import os
import pandas as pd
import streamlit as st


def get_data_filepath(filename: str) -> str:
    """Procura o arquivo no diretório `./data/` ou na raiz do projeto."""
    possible_paths = [
        os.path.join("./data", filename),
        filename,
        os.path.join("./data", "RELAÇÃO CUSTO FRETES_2026-08_09.xlsx") if "Frete" in filename else "",
        "RELAÇÃO CUSTO FRETES_2026-08_09.xlsx" if "Frete" in filename else "",
    ]
    for p in possible_paths:
        if p and os.path.exists(p):
            return p
    return ""


@st.cache_data(ttl=60, show_spinner=False)
def load_dados_producao() -> pd.DataFrame:
    """Carrega a base de produção resgatando PVs, SKUs, Saudável e Backlog."""
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

        # 2. Resgate de Saudável e Backlog
        if "DadosBacklogXSaudavel" in sheets:
            df_bs = pd.read_excel(excel, sheet_name="DadosBacklogXSaudavel")
            df_bs["DATA"] = pd.to_datetime(df_bs["DATA"], errors="coerce").astype("datetime64[ns]")
            df_prod = pd.merge(df_limpeza, df_bs[["DATA", "Saudavel", "Backlog"]], on="DATA", how="outer")
        else:
            df_prod = df_limpeza.copy()
            df_prod["Saudavel"] = 0
            df_prod["Backlog"] = 0

        # 3. Resgate de Total SKUs
        if "DadosBrutos" in sheets:
            df_brutos = pd.read_excel(excel, sheet_name="DadosBrutos")
            df_brutos["DATA"] = pd.to_datetime(df_brutos["DATA"], errors="coerce").astype("datetime64[ns]")
            col_sku = "SKU'S" if "SKU'S" in df_brutos.columns else ("SKUS" if "SKUS" in df_brutos.columns else df_brutos.columns[0])
            df_skus = df_brutos.groupby("DATA")[col_sku].count().reset_index(name="Total_SKUs")
            df_prod = pd.merge(df_prod, df_skus, on="DATA", how="outer")
        else:
            df_prod["Total_SKUs"] = df_prod["Quantidade"]

        df_prod["Quantidade"] = pd.to_numeric(df_prod["Quantidade"], errors="coerce").fillna(0)
        df_prod["Saudavel"] = pd.to_numeric(df_prod["Saudavel"], errors="coerce").fillna(0)
        df_prod["Backlog"] = pd.to_numeric(df_prod["Backlog"], errors="coerce").fillna(0)
        df_prod["Total_SKUs"] = pd.to_numeric(df_prod["Total_SKUs"], errors="coerce").fillna(0)

        return df_prod.dropna(subset=["DATA"]).sort_values("DATA").reset_index(drop=True)

    except Exception as e:
        st.error(f"Erro ao carregar DadosProducao.xlsx: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=60, show_spinner=False)
def load_dados_romaneio() -> pd.DataFrame:
    """Carrega a base de Romaneios / Expedição."""
    filepath = get_data_filepath("DadosRomaneio.xlsx")
    if not filepath:
        return pd.DataFrame()

    try:
        df_rom = pd.read_excel(filepath)
        col_data = [c for c in df_rom.columns if str(c).strip().upper() == "DATA"]
        if col_data:
            df_rom["DATA"] = pd.to_datetime(df_rom[col_data[0]], errors="coerce").astype("datetime64[ns]")
        return df_rom
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=60, show_spinner=False)
def load_dados_faturamento() -> tuple:
    """Carrega Faturamento Bruto por Filial e Faturamento Detalhado por Cliente."""
    filepath = get_data_filepath("DadosFaturamento.xlsx")
    if not filepath:
        return pd.DataFrame(), pd.DataFrame()

    try:
        excel = pd.ExcelFile(filepath)
        df_fat_bruto_raw = (
            pd.read_excel(excel, sheet_name="FaturamentoBruto", header=None)
            if "FaturamentoBruto" in excel.sheet_names
            else pd.DataFrame()
        )
        df_fat_detalhado = (
            pd.read_excel(excel, sheet_name="Faturamento por cliente")
            if "Faturamento por cliente" in excel.sheet_names
            else pd.DataFrame()
        )
        return df_fat_bruto_raw, df_fat_detalhado
    except Exception as e:
        st.error(f"Erro ao carregar DadosFaturamento.xlsx: {e}")
        return pd.DataFrame(), pd.DataFrame()


@st.cache_data(ttl=60, show_spinner=False)
def load_dados_frete() -> pd.DataFrame:
    """Carrega os lançamentos diários de frete terceirizado com suporte a múltiplos nomes de colunas."""
    filepath = get_data_filepath("DadosFrete.xlsx")
    if not filepath:
        return pd.DataFrame()

    try:
        df_frete = pd.read_excel(filepath)
        
        # Mapeamento estrito para planilhas brutas ou tratadas
        col_data = "EMISSÃO CTE/NFE" if "EMISSÃO CTE/NFE" in df_frete.columns else ("DATA" if "DATA" in df_frete.columns else df_frete.columns[0])
        col_frete = "VL. FRETE" if "VL. FRETE" in df_frete.columns else ("Valor Total Frete" if "Valor Total Frete" in df_frete.columns else df_frete.columns[1])

        df_frete["DATA"] = pd.to_datetime(df_frete[col_data], errors="coerce").astype("datetime64[ns]")
        df_frete["Valor Total Frete"] = pd.to_numeric(df_frete[col_frete], errors="coerce").fillna(0.0)

        return df_frete.dropna(subset=["DATA"]).sort_values("DATA").reset_index(drop=True)
    except Exception as e:
        st.error(f"Erro ao carregar dados de frete: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=60, show_spinner=False)
def load_resumo_terceiros_MNOP() -> pd.DataFrame:
    """Carrega o resumo por transportadora terceirizada para os gráficos de pizza."""
    filepath = get_data_filepath("DadosFrete.xlsx")
    if not filepath:
        return pd.DataFrame()

    try:
        df_raw = pd.read_excel(filepath)
        
        # Leitura da tabela dinâmica presente na planilha de frete (Colunas da direita)
        if "Rótulos de Linha" in df_raw.columns:
            df_mnop = df_raw[["Rótulos de Linha", "Soma de Vlr_Nota_Fiscal", "Soma de VL. FRETE", "%"]].dropna(subset=["Rótulos de Linha"]).copy()
            df_mnop.columns = ["Transportadora", "Valor_NF", "Valor_Frete", "Pct_Frete"]
        else:
            df_mnop = df_raw.copy()
            renames = {}
            for c in df_mnop.columns:
                c_str = str(c).strip().upper()
                if "TRANSP" in c_str:
                    renames[c] = "Transportadora"
                elif "VALOR" in c_str and "NF" in c_str:
                    renames[c] = "Valor_NF"
                elif "FRETE" in c_str:
                    renames[c] = "Valor_Frete"
                elif "%" in c_str:
                    renames[c] = "Pct_Frete"
            if renames:
                df_mnop.rename(columns=renames, inplace=True)

        df_mnop["Valor_NF"] = pd.to_numeric(df_mnop["Valor_NF"], errors="coerce").fillna(0.0)
        df_mnop["Valor_Frete"] = pd.to_numeric(df_mnop["Valor_Frete"], errors="coerce").fillna(0.0)
        df_mnop["Pct_Frete"] = pd.to_numeric(df_mnop["Pct_Frete"], errors="coerce").fillna(0.0)

        return df_mnop
    except Exception as e:
        st.error(f"Erro ao carregar resumo MNOP de frete: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=60, show_spinner=False)
def load_treated_data_cached():
    """Função central mantida para compatibilidade com o app.py."""
    df_prod_tratado = load_dados_producao()
    df_rom_tratado = load_dados_romaneio()
    df_fat_bruto_raw, df_fat_detalhado = load_dados_faturamento()
    df_frete_tratado = load_dados_frete()

    return (
        df_prod_tratado,
        df_rom_tratado,
        df_fat_detalhado,
        df_fat_bruto_raw,
        df_frete_tratado,
    )