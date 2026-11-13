import pandas as pd


def parse_faturamento_filiais(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Extrai e padroniza o faturamento bruto e as devoluções por filial da aba FaturamentoBruto."""
    if df_raw is None or df_raw.empty:
        return pd.DataFrame()

    df = df_raw.copy()
    df.columns = [str(c).strip() for c in df.columns]

    # Remove a linha de sub-cabeçalho ("Fat." / "Dev.") onde Data é NaT
    df["DATA"] = pd.to_datetime(df["Data"], errors="coerce").dt.normalize()
    df = df.dropna(subset=["DATA"]).copy()

    col_map = {
        "0101 - Matriz": ("0101 - Matriz_Fat", "Unnamed: 2", "0101 - Matriz_Dev"),
        "0102 - Filial RJ": ("0102 - Filial RJ_Fat", "Unnamed: 4", "0102 - Filial RJ_Dev"),
        "0103 - Filial CP": ("0103 - Filial CP_Fat", "Unnamed: 6", "0103 - Filial CP_Dev"),
        "0104 - Filial SBC": ("0104 - Filial SBC_Fat", "Unnamed: 8", "0104 - Filial SBC_Dev"),
    }

    out = pd.DataFrame()
    out["DATA"] = df["DATA"]

    soma_fat_filiais = pd.Series(0.0, index=df.index)
    soma_dev_filiais = pd.Series(0.0, index=df.index)

    for col_orig_fat, (col_dest_fat, col_orig_dev, col_dest_dev) in col_map.items():
        val_fat = pd.to_numeric(df[col_orig_fat], errors="coerce").fillna(0.0) if col_orig_fat in df.columns else 0.0
        val_dev = pd.to_numeric(df[col_orig_dev], errors="coerce").fillna(0.0) if col_orig_dev in df.columns else 0.0

        # Garante devolução sempre <= 0
        val_dev_neg = -val_dev.abs() if isinstance(val_dev, pd.Series) else -abs(val_dev)

        out[col_dest_fat] = val_fat
        out[col_dest_dev] = val_dev_neg

        soma_fat_filiais += val_fat
        soma_dev_filiais += val_dev_neg

    # Coluna DEV oficial (sempre <= 0)
    if "DEV" in df.columns:
        dev_tot = -pd.to_numeric(df["DEV"], errors="coerce").fillna(0.0).abs()
    else:
        dev_tot = soma_dev_filiais

    # Coluna TOT da planilha já vem descontando as devoluções (Líquido).
    # Portanto, o Faturamento Bruto Geral = TOT + |DEV| (ou soma das filiais), e o Líquido = TOT.
    if "TOT" in df.columns:
        tot_liq = pd.to_numeric(df["TOT"], errors="coerce").fillna(0.0)
        out["Todas as Unidades (Geral)_Liq"] = tot_liq
        out["Todas as Unidades (Geral)_Fat"] = tot_liq + dev_tot.abs()
    else:
        out["Todas as Unidades (Geral)_Fat"] = soma_fat_filiais
        out["Todas as Unidades (Geral)_Liq"] = soma_fat_filiais - dev_tot.abs()

    out["Todas as Unidades (Geral)_Dev"] = dev_tot

    return out.groupby("DATA", as_index=False).sum().sort_values("DATA").reset_index(drop=True)