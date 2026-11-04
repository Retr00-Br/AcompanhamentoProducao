import pandas as pd
import streamlit as st
from utils.loader import load_resumo_terceiros_MNOP
from utils.parser import fmt_brl


def render_secao_frete(df_filtrado: pd.DataFrame = None, col_fat_ativa: str = None, df_frete_bruto: pd.DataFrame = None):
    st.divider()
    st.markdown("### 🚚 Resumo do Custo de Frete Terceirizado por Transportadora")

    # Leitura exclusiva das colunas M, N, O e P
    df_mnop = load_resumo_terceiros_MNOP()

    if df_mnop.empty:
        st.info("Tabela de frete por transportadora indisponível (Colunas M, N, O, P).")
        return

    # Tratar e separar a linha de Total Geral
    df_corpo = df_mnop[df_mnop["Transportadora"].astype(str).str.strip().str.upper() != "TOTAL GERAL"].copy()
    df_total = df_mnop[df_mnop["Transportadora"].astype(str).str.strip().str.upper() == "TOTAL GERAL"].copy()

    # Ordenar o corpo pelo maior Valor de Frete
    df_corpo = df_corpo.sort_values(by="Valor_Frete", ascending=False).reset_index(drop=True)

    # Reanexar o Total Geral no final
    df_exibicao = pd.concat([df_corpo, df_total], ignore_index=True)

    # Métricas de topo (Cards KPIs)
    vlr_frete_acumulado = df_total["Valor_Frete"].sum() if not df_total.empty else df_corpo["Valor_Frete"].sum()
    vlr_nf_acumulado = df_total["Valor_NF"].sum() if not df_total.empty else df_corpo["Valor_NF"].sum()
    pct_media_geral = (vlr_frete_acumulado / vlr_nf_acumulado * 100) if vlr_nf_acumulado > 0 else 0.0

    k1, k2, k3 = st.columns(3)
    k1.metric("💵 Total Frete Acumulado (Coluna O)", fmt_brl(vlr_frete_acumulado))
    k2.metric("📦 Total NF Atendida (Coluna N)", fmt_brl(vlr_nf_acumulado))
    k3.metric("📊 % Frete Médio / NF (Coluna P)", f"{pct_media_geral:.2f}%")

    st.markdown("---")
    st.markdown("#### 📊 Acumulado Geral por Transportadora (Colunas M, N, O, P)")

    # Formatação sem marcadores HTML (texto limpo e puro)
    df_formatado = df_exibicao.copy()
    df_formatado["Valor NF (R$)"] = df_formatado["Valor_NF"].apply(fmt_brl)
    df_formatado["Valor Frete (R$)"] = df_formatado["Valor_Frete"].apply(fmt_brl)
    df_formatado["% Frete / NF"] = (df_formatado["Pct_Frete"] * 100).map("{:.2f}%".format)

    df_final = df_formatado[["Transportadora", "Valor NF (R$)", "Valor Frete (R$)", "% Frete / NF"]]

    # Renderizar a tabela interativa limpa
    st.dataframe(
        df_final,
        use_container_width=True,
        hide_index=True,
        height=min(600, len(df_final) * 38 + 40),
    )