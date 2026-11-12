import pandas as pd


def parse_faturamento_filiais(df_fat_bruto: pd.DataFrame) -> pd.DataFrame:
    """Processa a aba FaturamentoBruto separando Faturamento e Devolução de cada unidade."""
    if df_fat_bruto is None or df_fat_bruto.empty:
        return pd.DataFrame()

    df = df_fat_bruto.copy()
    df = df.dropna(subset=["Data"]).reset_index(drop=True)
    df["DATA"] = pd.to_datetime(df["Data"], errors="coerce").astype("datetime64[ns]")
    df = df.dropna(subset=["DATA"]).reset_index(drop=True)

    mapeamento = {
        "0101 - Matriz": ("0101 - Matriz", "Unnamed: 2"),
        "0102 - Filial RJ": ("0102 - Filial RJ", "Unnamed: 4"),
        "0103 - Filial CP": ("0103 - Filial CP", "Unnamed: 6"),
        "0104 - Filial SBC": ("0104 - Filial SBC", "Unnamed: 8"),
    }

    df_out = pd.DataFrame({"DATA": df["DATA"]})

    for unidade, (col_f, col_d) in mapeamento.items():
        val_f = pd.to_numeric(df[col_f], errors="coerce").fillna(0.0) if col_f in df.columns else 0.0
        val_d = pd.to_numeric(df[col_d], errors="coerce").fillna(0.0).abs() if col_d in df.columns else 0.0
        df_out[f"{unidade}_Fat"] = val_f
        df_out[f"{unidade}_Dev"] = val_d

    df_out["Todas as Unidades (Geral)_Fat"] = (
        df_out["0101 - Matriz_Fat"]
        + df_out["0102 - Filial RJ_Fat"]
        + df_out["0103 - Filial CP_Fat"]
        + df_out["0104 - Filial SBC_Fat"]
    )
    df_out["Todas as Unidades (Geral)_Dev"] = (
        df_out["0101 - Matriz_Dev"]
        + df_out["0102 - Filial RJ_Dev"]
        + df_out["0103 - Filial CP_Dev"]
        + df_out["0104 - Filial SBC_Dev"]
    )

    return df_out.groupby("DATA", as_index=False).sum().sort_values("DATA").reset_index(drop=True)