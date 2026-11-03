import os
import pandas as pd
import streamlit as st
from utils.security import DataSecurityManager


class DataLoader:
    """Carregador de dados ultrarrápido utilizando caching nativo do Streamlit."""

    DATA_DIR = "./data/"

    def __init__(self, key: bytes = None):
        self.key = key

    def _get_target_path(self, filename: str) -> str:
        path = os.path.join(self.DATA_DIR, filename)
        if os.path.exists(path):
            return path
        if os.path.exists(filename):
            return filename
        return None

    def read_dataframe(self, filename: str, sheet_name=0, header=0) -> pd.DataFrame:
        target_path = self._get_target_path(filename)
        if not target_path:
            return None

        enc_path = target_path + ".enc"
        if self.key and os.path.exists(enc_path):
            try:
                return DataSecurityManager.load_encrypted_excel(enc_path, self.key, sheet_name)
            except Exception:
                pass

        try:
            return pd.read_excel(target_path, sheet_name=sheet_name, header=header)
        except Exception:
            try:
                return pd.read_excel(target_path, sheet_name=0, header=header)
            except Exception:
                return None


@st.cache_data(ttl=3600, show_spinner=False)
def load_frete_multisheets_cached(filename: str = "SOLICITACAO TERCEIROS.xlsx", data_dir: str = "./data/") -> pd.DataFrame:
    """Consolida todas as abas da planilha de fretes terceirizados em cache."""
    target_path = os.path.join(data_dir, filename)
    if not os.path.exists(target_path) and os.path.exists(filename):
        target_path = filename

    if not target_path or not os.path.exists(target_path):
        return pd.DataFrame()

    try:
        xls = pd.ExcelFile(target_path)
        frames = []
        
        for sheet in xls.sheet_names:
            df = pd.read_excel(target_path, sheet_name=sheet)
            
            # Trata cabeçalhos descolados
            if df.shape[0] > 0 and df.shape[1] > 1 and df.iloc[0, 0] == "Data da solicitação":
                df.columns = df.iloc[0]
                df = df.iloc[1:]
            
            if "Data da solicitação" in df.columns:
                df_clean = df.dropna(subset=["Data da solicitação"]).copy()
                frames.append(df_clean)

        if frames:
            df_frete_all = pd.concat(frames, ignore_index=True)
            df_frete_all["DATA"] = pd.to_datetime(df_frete_all["Data da solicitação"], errors="coerce")
            df_frete_all = df_frete_all.dropna(subset=["DATA"]).copy()
            df_frete_all["Valor Total Frete"] = pd.to_numeric(
                df_frete_all["Valor Total Frete"], errors="coerce"
            ).fillna(0.0)
            return df_frete_all[["DATA", "Valor Total Frete"]]
    except Exception:
        pass

    return pd.DataFrame()


@st.cache_data(ttl=3600, show_spinner="Carregando e indexando bases de dados...")
def load_all_raw_data_cached():
    loader = DataLoader()
    df_prod_bruto = loader.read_dataframe("DadosProducao.xlsx", "DadosBrutos")
    df_prod_tratado = loader.read_dataframe("DadosProducao.xlsx", "LimpezaDados")

    df_rom_tratado = loader.read_dataframe("DadosRomaneios.xlsx", "DadosRomaneios")
    if df_rom_tratado is None:
        df_rom_tratado = loader.read_dataframe("DadosRomaneios.xlsx", "Planilha1")

    df_fat_detalhado = loader.read_dataframe("DadosFaturamento.xlsx", "Faturamento por cliente")
    if df_fat_detalhado is None:
        df_fat_detalhado = loader.read_dataframe("DadosFaturamento.xlsx", 0)

    df_fat_bruto_raw = loader.read_dataframe("DadosFaturamento.xlsx", "FaturamentoBruto", header=None)
    df_frete_raw = load_frete_multisheets_cached("SOLICITACAO TERCEIROS.xlsx")

    return (
        df_prod_bruto,
        df_prod_tratado,
        df_rom_tratado,
        df_fat_detalhado,
        df_fat_bruto_raw,
        df_frete_raw,
    )