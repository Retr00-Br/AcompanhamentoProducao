import pandas as pd


def fmt_brl(val: float) -> str:
    """Retorna o valor monetário formatado em Real (R$) limpo."""
    try:
        if pd.isna(val) or val is None:
            return "R$ 0,00"
        val = float(val)
        return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"


def parse_faturamento_filiais(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Extrai os dados da aba FaturamentoBruto mapeando as colunas das filiais corretamente."""
    if df_raw is None or df_raw.empty:
        return pd.DataFrame()

    try:
        # A partir da linha index 2 estão os dados diários
        df = df_raw.iloc[2:].copy()

        mapping_cols = {
            0: "DATA",
            1: "0101 - Matriz_Fat",
            2: "0101 - Matriz_Dev",
            3: "0102 - Filial RJ_Fat",
            4: "0102 - Filial RJ_Dev",
            5: "0103 - Filial CP_Fat",
            6: "0103 - Filial CP_Dev",
            7: "0104 - Filial SBC_Fat",
            8: "0104 - Filial SBC_Dev",
            9: "Todas as Unidades (Geral)_Fat",
            10: "Todas as Unidades (Geral)_Dev",
        }

        df = df.rename(columns=mapping_cols)
        df["DATA"] = pd.to_datetime(df["DATA"], errors="coerce")

        for col in df.columns:
            if col != "DATA":
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

        return df.dropna(subset=["DATA"]).reset_index(drop=True)
    except Exception:
        return pd.DataFrame()