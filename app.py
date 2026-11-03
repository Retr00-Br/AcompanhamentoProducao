import os
import pandas as pd
import streamlit as st

from utils.loader import load_treated_data_cached
from utils.parser import parse_faturamento_filiais
from components.ui_config import DashboardUI
from components.kpis import render_kpis_gerais, render_kpis_medias
from components.charts_faturamento import render_secao_faturamento
from components.charts_producao import render_graficos_producao
from components.charts_frete import render_secao_frete
from components.tables import render_top10_faturamento, render_tabela_consolidada

st.set_page_config(
    page_title="Dashboard Operacional & BI - Higimed",
    page_icon="📦",
    layout="wide",
)


@st.cache_data(ttl=1800, show_spinner=False)
def build_processed_dataset():
    """Consolida os dados integrando o SKU real da base sem gargalos de memória."""
    (
        df_prod_tratado,
        df_rom_tratado,
        df_fat_detalhado,
        df_fat_bruto_raw,
        df_frete_tratado,
    ) = load_treated_data_cached()

    if df_prod_tratado.empty or df_rom_tratado.empty:
        return None, None

    df_fat_unidades = parse_faturamento_filiais(df_fat_bruto_raw)

    # 1. Base Produção (PVs + Status + SKUs)
    df_diario = df_prod_tratado.copy()
    df_diario.rename(
        columns={
            "Quantidade": "Total_PVs",
            "Saudavel": "SAUDAVEL",
            "Backlog": "BACKLOG",
        },
        inplace=True,
    )

    if "Total_SKUs" in df_diario.columns:
        df_diario["Total_SKUs"] = pd.to_numeric(df_diario["Total_SKUs"], errors="coerce").fillna(0)
    else:
        df_diario["Total_SKUs"] = 0

    # 2. Romaneios
    df_r = df_rom_tratado.groupby("DATA")["Qtd. Expedição"].sum().reset_index(name="Total_Expedidos")
    df_diario = pd.merge(df_diario, df_r, on="DATA", how="outer").fillna(0)

    # 3. Faturamento
    if not df_fat_unidades.empty:
        df_diario = pd.merge(df_diario, df_fat_unidades, on="DATA", how="outer").fillna(0)

    # 4. Fretes Terceirizados
    if not df_frete_tratado.empty and "Total_Frete" not in df_diario.columns:
        df_frete_agg = (
            df_frete_tratado.groupby("DATA")
            .agg({"Valor Total Frete": "sum", "Valor Total NF": "sum"})
            .reset_index()
            .rename(columns={"Valor Total Frete": "Total_Frete", "Valor Total NF": "Total_NF_Frete"})
        )
        df_diario = pd.merge(df_diario, df_frete_agg, on="DATA", how="left").fillna(
            {"Total_Frete": 0.0, "Total_NF_Frete": 0.0}
        )

    if "Total_Frete" not in df_diario.columns:
        df_diario["Total_Frete"] = 0.0
        df_diario["Total_NF_Frete"] = 0.0

    df_diario = df_diario.dropna(subset=["DATA"]).sort_values("DATA").reset_index(drop=True)
    return df_diario, df_fat_detalhado


def main():
    ui = DashboardUI()
    ui.render_header()

    # Botão de emergência na barra lateral para limpar cache caso necessário
    with st.sidebar:
        st.markdown("### ⚙️ Gestão de Cache")
        if st.button("🔄 Limpar Cache e Forçar Atualização"):
            st.cache_data.clear()
            st.rerun()

    os.makedirs("./data/", exist_ok=True)
    df_diario, df_fat_detalhado = build_processed_dataset()

    if df_diario is None:
        st.info("📂 **Aguardando dados no Back-End:** Insira as planilhas no diretório `./data/` para sincronização.")
        st.stop()

    # FILTRO TEMPORAL
    st.subheader("📅 Filtro Temporal de Análise Operacional")
    col_ft1, col_ft2 = st.columns([1.5, 3])

    with col_ft1:
        tipo_filtro = st.radio(
            "Filtrar período por:",
            ["Intervalo de Calendário", "Por Mês", "Por Semana do Ano"],
            horizontal=True,
        )

    df_valido = df_diario[df_diario["Total_PVs"] > 0] if not df_diario[df_diario["Total_PVs"] > 0].empty else df_diario
    min_date = df_valido["DATA"].min().date()
    max_date = df_valido["DATA"].max().date()

    with col_ft2:
        if tipo_filtro == "Intervalo de Calendário":
            data_sel = st.date_input(
                "Selecione o Período:",
                value=(min_date, max_date),
                min_value=df_diario["DATA"].min().date(),
                max_value=df_diario["DATA"].max().date(),
            )
            dt_inicio, dt_fim = data_sel if isinstance(data_sel, tuple) and len(data_sel) == 2 else (min_date, max_date)
        elif tipo_filtro == "Por Mês":
            df_diario["Mes_Ano"] = df_diario["DATA"].dt.strftime("%Y-%m")
            meses = sorted(df_diario["Mes_Ano"].unique().tolist())
            mes_sel = st.selectbox("Selecione o Mês:", meses, index=len(meses) - 1)
            dt_inicio = df_diario[df_diario["Mes_Ano"] == mes_sel]["DATA"].min().date()
            dt_fim = df_diario[df_diario["Mes_Ano"] == mes_sel]["DATA"].max().date()
        else:
            df_diario["Semana"] = (
                "Semana "
                + df_diario["DATA"].dt.isocalendar().week.astype(str)
                + " / "
                + df_diario["DATA"].dt.year.astype(str)
            )
            semanas = df_diario["Semana"].unique().tolist()
            semana_sel = st.selectbox("Selecione a Semana:", semanas, index=len(semanas) - 1)
            dt_inicio = df_diario[df_diario["Semana"] == semana_sel]["DATA"].min().date()
            dt_fim = df_diario[df_diario["Semana"] == semana_sel]["DATA"].max().date()

    # Aplicação do Filtro Temporal
    df_filtrado = df_diario[
        (df_diario["DATA"].dt.date >= dt_inicio) & (df_diario["DATA"].dt.date <= dt_fim)
    ].copy().sort_values("DATA").reset_index(drop=True)

    # Purga da data de teste 02/01
    df_filtrado = df_filtrado[df_filtrado["DATA"].dt.strftime("%d/%m") != "02/01"].reset_index(drop=True)

    df_filtrado["Data_Str"] = df_filtrado["DATA"].dt.strftime("%d/%m")

    # Seletor de Filial
    opcoes_filiais = [
        "Todas as Unidades (Geral)",
        "0101 - Matriz",
        "0102 - Filial RJ",
        "0103 - Filial CP",
        "0104 - Filial SBC",
    ]
    unidade_selecionada = st.selectbox("🏢 Selecione a Unidade / Filial:", opcoes_filiais, index=0)

    col_fat_ativa = f"{unidade_selecionada}_Fat"
    col_dev_ativa = f"{unidade_selecionada}_Dev"

    # Renderização da Aplicação
    render_kpis_gerais(df_filtrado)
    render_secao_faturamento(df_filtrado, unidade_selecionada)
    render_kpis_medias(df_filtrado, unidade_selecionada)
    render_graficos_producao(df_filtrado, col_fat_ativa, unidade_selecionada)
    render_secao_frete(df_filtrado, col_fat_ativa)
    render_top10_faturamento(df_fat_detalhado, unidade_selecionada)
    render_tabela_consolidada(df_filtrado, col_fat_ativa, col_dev_ativa)


if __name__ == "__main__":
    main()