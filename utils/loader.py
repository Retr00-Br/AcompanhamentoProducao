import os
import pandas as pd
from utils.security import DataSecurityManager


class DataLoader:
    """Lê as planilhas diretamente do diretório back-end ./data/ ou da raiz."""

    DATA_DIR = "./data/"

    def __init__(self, key: bytes = None):
        self.key = key

    def read_dataframe(self, filename: str, sheet_name=0, header=0) -> pd.DataFrame:
        path = os.path.join(self.DATA_DIR, filename)
        enc_path = path + ".enc"

        if self.key and os.path.exists(enc_path):
            try:
                return DataSecurityManager.load_encrypted_excel(enc_path, self.key, sheet_name)
            except Exception:
                pass

        if os.path.exists(path):
            try:
                return pd.read_excel(path, sheet_name=sheet_name, header=header)
            except Exception:
                try:
                    return pd.read_excel(path, sheet_name=0, header=header)
                except Exception:
                    return None

        if os.path.exists(filename):
            try:
                return pd.read_excel(filename, sheet_name=sheet_name, header=header)
            except Exception:
                try:
                    return pd.read_excel(filename, sheet_name=0, header=header)
                except Exception:
                    return None

        return None

    def load_all_data(self):
        df_prod_bruto = self.read_dataframe("DadosProducao.xlsx", "DadosBrutos")
        df_prod_tratado = self.read_dataframe("DadosProducao.xlsx", "LimpezaDados")

        df_rom_tratado = self.read_dataframe("DadosRomaneios.xlsx", "DadosRomaneios")
        if df_rom_tratado is None:
            df_rom_tratado = self.read_dataframe("DadosRomaneios.xlsx", "Planilha1")

        df_fat_detalhado = self.read_dataframe("DadosFaturamento.xlsx", "Faturamento por cliente")
        if df_fat_detalhado is None:
            df_fat_detalhado = self.read_dataframe("DadosFaturamento.xlsx", 0)

        df_fat_bruto_raw = self.read_dataframe("DadosFaturamento.xlsx", "FaturamentoBruto", header=None)

        # Leitura da planilha de solicitações de frete terceirizado
        df_frete_raw = self.read_dataframe("SOLICITACAO TERCEIROS.xlsx", "2026")

        return (
            df_prod_bruto,
            df_prod_tratado,
            df_rom_tratado,
            df_fat_detalhado,
            df_fat_bruto_raw,
            df_frete_raw,
        )