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

        target_path = path if os.path.exists(path) else (filename if os.path.exists(filename) else None)
        if target_path:
            try:
                return pd.read_excel(target_path, sheet_name=sheet_name, header=header)
            except Exception:
                try:
                    return pd.read_excel(target_path, sheet_name=0, header=header)
                except Exception:
                    return None

        return None

    def load_frete_multisheets(self, filename: str = "SOLICITACAO TERCEIROS.xlsx") -> pd.DataFrame:
        """Carrega e consolida todas as abas contendo dados de frete (ex: '2026', '26', 'TJ')."""
        target_path = os.path.join(self.DATA_DIR, filename)
        if not os.path.exists(target_path) and os.path.exists(filename):
            target_path = filename

        if not target_path or not os.path.exists(target_path):
            return pd.DataFrame()

        try:
            xls = pd.ExcelFile(target_path)
            frames = []
            
            # Percorre abas de interesse ou todas com a coluna Data
            for sheet in xls.sheet_names:
                df = pd.read_excel(target_path, sheet_name=sheet)
                
                # Trata cabeçalho caso esteja na primeira linha (aba TJ)
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
                return df_frete_all
        except Exception:
            pass

        return pd.DataFrame()

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

        # Leitura consolidada da planilha de solicitações de frete
        df_frete_raw = self.load_frete_multisheets("SOLICITACAO TERCEIROS.xlsx")

        return (
            df_prod_bruto,
            df_prod_tratado,
            df_rom_tratado,
            df_fat_detalhado,
            df_fat_bruto_raw,
            df_frete_raw,
        )