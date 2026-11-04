@st.cache_data(ttl=1800, show_spinner=False)
def load_resumo_terceiros_MNOP():
    """Lê diretamente as Colunas M, N, O e P da planilha de Fretes."""
    data_dir = "./data/"

    def get_path(filename):
        paths_to_check = [
            os.path.join(data_dir, filename),
            filename,
            os.path.join(data_dir, filename.upper()),
            filename.upper(),
        ]
        for p in paths_to_check:
            if os.path.exists(p):
                return p
        return None

    path_frete = (
        get_path("RELAÇÃO CUSTO FRETES_2026-08_09_3.xlsx")
        or get_path("RELAÇÃO CUSTO FRETES_2026-08_09_2.xlsx")
        or get_path("RELAÇÃO CUSTO FRETES_2026-08_09.xlsx")
        or get_path("SOLICITACAO TERCEIROS.xlsx")
    )

    if not path_frete:
        return pd.DataFrame()

    try:
        df_raw = pd.read_excel(path_frete, sheet_name=0)
        
        # Coluna M (idx 12), N (idx 13), O (idx 14), P (idx 15)
        df_mnop = df_raw.iloc[:, 12:16].dropna(subset=[df_raw.columns[12]]).copy()
        df_mnop.columns = ["Transportadora", "Valor_NF", "Valor_Frete", "Pct_Frete"]

        df_mnop["Transportadora"] = df_mnop["Transportadora"].astype(str).str.strip()
        df_mnop["Valor_NF"] = pd.to_numeric(df_mnop["Valor_NF"], errors="coerce").fillna(0.0)
        df_mnop["Valor_Frete"] = pd.to_numeric(df_mnop["Valor_Frete"], errors="coerce").fillna(0.0)
        df_mnop["Pct_Frete"] = pd.to_numeric(df_mnop["Pct_Frete"], errors="coerce").fillna(0.0)

        return df_mnop
    except Exception:
        return pd.DataFrame()