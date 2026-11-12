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
    """Localiza a planilha de Custo de Fretes mais recente (por data de modificação) em ./data/ ou na raiz."""
    candidatos = []
    for folder in ["./data/", "."]:
        if os.path.exists(folder):
            for fname in os.listdir(folder):
                if "FRETE" in fname.upper() and fname.endswith(".xlsx") and not fname.startswith("~$"):
                    full_path = os.path.join(folder, fname)
                    candidatos.append((os.path.getmtime(full_path), full_path))

    if not candidatos:
        return ""

    # Ordena do mais recente para o mais antigo para garantir leitura da versão mais nova (_4.xlsx, etc.)
    candidatos.sort(key=lambda x: x[0], reverse=True)
    return candidatos[0][1]


def _get_files_signature() -> str:
    """Gera uma assinatura baseada no nome e timestamp dos arquivos Excel para invalidar cache ao atualizar planilhas."""
    sigs = []
    for folder in ["./data/", "."]:
        if os.path.exists(folder):
            for fname in sorted(os.listdir(folder)):
                if fname.endswith(".xlsx") and not fname.startswith("~$"):
                    fp = os.path.join(folder, fname)
                    sigs.append(f"{fp}:{os.path.getmtime(fp)}:{os.path.getsize(fp)}")
    return "|".join(sigs)


@st.cache_data(ttl=60, show_spinner=False)
def load_dados_producao(_sig: str = "") -> pd.DataFrame:
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

        df_limpeza.columns = [str(c).strip() for c in df_limpeza.columns]
        df_limpeza["DATA"] = pd.to_datetime(df_limpeza["DATA"], errors="coerce").dt.normalize()
        df_limpeza.rename(columns={"Quantidade": "Notas_Realizadas"}, inplace=True)
        df_limpeza["Quantidade"] = df_limpeza["Notas_Realizadas"]

        if "DadosBacklogXSaudavel" in sheets:
            df_bs = pd.read_excel(excel, sheet_name="DadosBacklogXSaudavel")
            df_bs.columns = [str(c).strip() for c in df_bs.columns]
            df_bs["DATA"] = pd.to_datetime(df_bs["DATA"], errors="coerce").dt.normalize()
            df_prod = pd.merge(df_limpeza, df_bs[["DATA", "Saudavel", "Backlog"]], on="DATA", how="outer")
        else:
            df_prod = df_limpeza.copy()
            df_prod["Saudavel"] = 0
            df_prod["Backlog"] = 0

        if "DadosBrutos" in sheets:
            df_brutos = pd.read_excel(excel, sheet_name="DadosBrutos")
            df_brutos.columns = [str(c).strip() for c in df_brutos.columns]
            df_brutos["DATA"] = pd.to_datetime(df_brutos["DATA"], errors="coerce").dt.normalize()
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
def load_dados_romaneios(_sig: str = "") -> pd.DataFrame:
    """Carrega os volumes expedidos da aba DadosRomaneios."""
    filepath = get_data_filepath("DadosRomaneios.xlsx")
    if not filepath:
        return pd.DataFrame()

    try:
        excel = pd.ExcelFile(filepath)
        sheet_target = "DadosRomaneios" if "DadosRomaneios" in excel.sheet_names else excel.sheet_names[0]
        df_rom = pd.read_excel(excel, sheet_name=sheet_target)
        df_rom.columns = [str(c).strip() for c in df_rom.columns]

        col_dt = "Dt. Romaneio" if "Dt. Romaneio" in df_rom.columns else df_rom.columns[0]
        col_qtd = "Qtd. Expedição" if "Qtd. Expedição" in df_rom.columns else df_rom.columns[1]

        df_rom.rename(columns={col_dt: "DATA", col_qtd: "Qtd. Expedição"}, inplace=True)
        df_rom["DATA"] = pd.to_datetime(df_rom["DATA"], errors="coerce").dt.normalize()
        df_rom["Qtd. Expedição"] = pd.to_numeric(df_rom["Qtd. Expedição"], errors="coerce").fillna(0)

        return df_rom.dropna(subset=["DATA"]).sort_values("DATA").reset_index(drop=True)

    except Exception as e:
        st.error(f"Erro ao carregar DadosRomaneios.xlsx: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=60, show_spinner=False)
def load_dados_faturamento(_sig: str = ""):
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
def load_dados_frete(_sig: str = "") -> pd.DataFrame:
    """Lê TODAS as abas/planilhas do arquivo de Custo de Fretes (ex: '08-09', '10', '11', etc.) e consolida tudo."""
    filepath = get_frete_filepath()
    if not filepath:
        return pd.DataFrame()

    try:
        # sheet_name=None lê todas as abas do arquivo Excel em um dicionário {nome_aba: DataFrame}
        todas_abas = pd.read_excel(filepath, sheet_name=None)
        dfs_abas = []

        for nome_aba, df_sheet in todas_abas.items():
            if df_sheet is None or df_sheet.empty:
                continue

            df_sheet.columns = [str(c).strip() for c in df_sheet.columns]
            col_data = None
            col_valor = None
            col_transp = None
            col_nf = None

            for c in df_sheet.columns:
                c_up = c.upper()
                if "EMISSÃO" in c_up or "EMISSAO" in c_up or c_up == "DATA":
                    col_data = c
                elif c_up == "VL. FRETE" or c_up == "VALOR FRETE":
                    col_valor = c
                elif c_up == "TRANSPORTADORA":
                    col_transp = c
                elif c_up in ["VLR_NOTA_FISCAL", "NOTA_FISCAL", "VLR NOTA FISCAL"]:
                    col_nf = c

            if col_data and col_valor:
                df_temp = pd.DataFrame()
                df_temp["DATA"] = pd.to_datetime(df_sheet[col_data], errors="coerce").dt.normalize()
                df_temp["Valor Total Frete"] = pd.to_numeric(df_sheet[col_valor], errors="coerce").fillna(0.0)
                df_temp["Transportadora"] = (
                    df_sheet[col_transp].astype(str).str.strip().str.upper()
                    if col_transp
                    else "NÃO INFORMADA"
                )
                df_temp["Valor_NF"] = (
                    pd.to_numeric(df_sheet[col_nf], errors="coerce").fillna(0.0)
                    if col_nf
                    else 0.0
                )
                df_temp["Aba_Origem"] = str(nome_aba).strip()

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
def load_resumo_terceiros_MNOP(_sig: str = "") -> pd.DataFrame:
    """Consolida o resumo por transportadora terceirizada de TODAS as abas da planilha de frete."""
    df_frete = load_dados_frete(_sig)
    if df_frete is not None and not df_frete.empty and "Transportadora" in df_frete.columns:
        df_valid = df_frete[
            ~df_frete["Transportadora"].isin(["NAN", "NONE", "", "NÃO INFORMADA"])
            & ~df_frete["Transportadora"].str.contains("TOTAL")
        ].copy()

        if not df_valid.empty:
            df_consolidado = df_valid.groupby("Transportadora", as_index=False).agg(
                Valor_NF=("Valor_NF", "sum"),
                Valor_Frete=("Valor Total Frete", "sum"),
            )
            df_consolidado["Pct_Frete"] = (
                df_consolidado["Valor_Frete"] / df_consolidado["Valor_NF"].replace(0, pd.NA)
            ).fillna(0.0)
            return df_consolidado.sort_values("Valor_Frete", ascending=False).reset_index(drop=True)

    return pd.DataFrame()


def load_treated_data_cached():
    """Carrega todas as bases unificadas invalidando o cache automaticamente se algum Excel mudar."""
    sig = _get_files_signature()
    df_prod = load_dados_producao(sig)
    df_rom = load_dados_romaneios(sig)
    df_fat_clientes, df_fat_bruto = load_dados_faturamento(sig)
    df_frete = load_dados_frete(sig)
    return df_prod, df_rom, df_fat_clientes, df_fat_bruto, df_frete