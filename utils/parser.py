import pandas as pd


def parse_faturamento_filiais(df_raw: pd.DataFrame) -> pd.DataFrame:
    if df_raw is None or df_raw.empty:
        return pd.DataFrame()

    df_data = df_raw.iloc[2:].copy()
    col_data = pd.to_datetime(df_data.iloc[:, 0], errors="coerce")

    matriz_fat = pd.to_numeric(df_data.iloc[:, 1], errors="coerce").fillna(0)
    matriz_dev = abs(pd.to_numeric(df_data.iloc[:, 2], errors="coerce").fillna(0))

    rj_fat = pd.to_numeric(df_data.iloc[:, 3], errors="coerce").fillna(0)
    rj_dev = abs(pd.to_numeric(df_data.iloc[:, 4], errors="coerce").fillna(0))

    cp_fat = pd.to_numeric(df_data.iloc[:, 5], errors="coerce").fillna(0)
    cp_dev = abs(pd.to_numeric(df_data.iloc[:, 6], errors="coerce").fillna(0))

    sbc_fat = pd.to_numeric(df_data.iloc[:, 7], errors="coerce").fillna(0)
    sbc_dev = abs(pd.to_numeric(df_data.iloc[:, 8], errors="coerce").fillna(0))

    tot_col_j = pd.to_numeric(df_data.iloc[:, 9], errors="coerce").fillna(0) if df_data.shape[1] > 9 else (matriz_fat + rj_fat + cp_fat + sbc_fat)
    dev_col_k = abs(pd.to_numeric(df_data.iloc[:, 10], errors="coerce").fillna(0)) if df_data.shape[1] > 10 else (matriz_dev + rj_dev + cp_dev + sbc_dev)

    df_fat = pd.DataFrame({
        "DATA": col_data,
        "0101 - Matriz_Fat": matriz_fat,
        "0101 - Matriz_Dev": matriz_dev,
        "0102 - Filial RJ_Fat": rj_fat,
        "0102 - Filial RJ_Dev": rj_dev,
        "0103 - Filial CP_Fat": cp_fat,
        "0103 - Filial CP_Dev": cp_dev,
        "0104 - Filial SBC_Fat": sbc_fat,
        "0104 - Filial SBC_Dev": sbc_dev,
        "Todas as Unidades (Geral)_Fat": tot_col_j,
        "Todas as Unidades (Geral)_Dev": dev_col_k,
    }).dropna(subset=["DATA"]).sort_values("DATA").reset_index(drop=True)

    return df_fat


def fmt_brl(val: float) -> str:
    if val >= 1_000_000:
        return f"<b>R$ {val/1_000_000:.2f}M</b>".replace(".", ",")
    elif val >= 1_000:
        return f"<b>R$ {val/1_000:.0f}k</b>"
    elif val > 0:
        return f"<b>R$ {val:.0f}</b>"
    return ""