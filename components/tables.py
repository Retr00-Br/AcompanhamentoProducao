import pandas as pd
import streamlit as st
from utils.parser import fmt_brl


def render_top10_faturamento(df_fat_detalhado: pd.DataFrame, unidade_selecionada: str):
    st.markdown("---")
    st.markdown("### 🏆 Faturamento por Cliente (3 Colunas)")

    if df_fat_detalhado.empty:
        st.info("Dados de faturamento por cliente indisponíveis.")
        return

    df_cli = df_fat_detalhado.copy()

    colunas_3 = [c for c in ["Filial", "Cliente", "R$ Fatur."] if c in df_cli.columns]
    df_cli = df_cli[colunas_3]

    if unidade_selecionada != "Todas as Unidades (Geral)":
        cod_filial = unidade_selecionada.split("-")[0].strip()
        df_cli = df_cli[df_cli["Filial"].astype(str).str.contains(cod_filial, na=False)]

    if df_cli.empty:
        st.info("Nenhum registro para a filial selecionada.")
        return

    df_exibicao = df_cli.copy()
    if "R$ Fatur." in df_exibicao.columns:
        df_exibicao["R$ Fatur."] = df_exibicao["R$ Fatur."].apply(fmt_brl)

    st.dataframe(
        df_exibicao,
        use_container_width=True,
        hide_index=True,
        height=min(500, len(df_exibicao) * 38 + 40),
    )


def render_tabela_consolidada(df_filtrado: pd.DataFrame, col_fat_ativa: str, col_dev_ativa: str):
    st.markdown("---")
    st.markdown("### 📑 Tabela Consolidada Diária de Operações")

    if df_filtrado.empty:
        st.info("Sem registros para exibição da tabela consolidada.")
        return

    df_tab = df_filtrado.copy()
    df_tab["Data"] = df_tab["DATA"].dt.strftime("%d/%m/%Y")

    cols = ["Data"]
    if col_fat_ativa in df_tab.columns:
        df_tab["Faturamento (R$)"] = df_tab[col_fat_ativa].apply(fmt_brl)
        cols.append("Faturamento (R$)")
    if col_dev_ativa in df_tab.columns:
        df_tab["Devoluções (R$)"] = df_tab[col_dev_ativa].apply(fmt_brl)
        cols.append("Devoluções (R$)")
    if "Total_PVs" in df_tab.columns:
        # Tratamento seguro contra NaN para evitar IntCastingNaNError
        df_tab["PVs"] = df_tab["Total_PVs"].fillna(0).astype(int)
        cols.append("PVs")
    if "Total_Expedidos" in df_tab.columns:
        df_tab["Expedidos"] = df_tab["Total_Expedidos"].fillna(0).astype(int)
        cols.append("Expedidos")
    if "Total_Frete" in df_tab.columns:
        df_tab["Frete (R$)"] = df_tab["Total_Frete"].apply(fmt_brl)
        cols.append("Frete (R$)")

    st.dataframe(
        df_tab[cols],
        use_container_width=True,
        hide_index=True,
        height=min(500, len(df_tab) * 38 + 40),
    )