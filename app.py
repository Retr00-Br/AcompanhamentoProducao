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
    """Unifica os dados de Produção, Faturamento e Frete no mesmo dataset diário harmonizando dtypes de DATA."""
    (
        df_prod_tratado,
        df_rom_tratado,
        df_fat_detalhado,
        df_fat_bruto_raw,
        df_frete_tratado,
    ) = load_treated_data_cached()

    df_fat_unidades = parse_faturamento_filiais(df_fat_bruto_raw)

    # 1. Base Produção
    df_diario = df_prod_tratado.copy()
    df_diario.rename(
        columns={
            "Quantidade": "Total_PVs",
            "Saudavel": "SAUDAVEL",
            "Backlog": "BACKLOG",
        },
        inplace=True,
    )

    # Harmonização estrita do tipo datetime na chave de merge
    df_diario["DATA"] = pd.to_datetime(df_diario["DATA"], errors="coerce").dt.normalize()

    if "Total_SKUs" in df_diario.columns:
        df_diario["Total_SKUs"] = pd.to_numeric(df_diario["Total_SKUs"], errors="coerce").fillna(0)
    else:
        df_diario["Total_SKUs"] = 0

    # 2. Romaneios
    if df_rom_tratado is not None and not df_rom_tratado.empty:
        df_r = df_rom_tratado.groupby("DATA")["Qtd. Expedição"].sum().reset_index(name="Total_Expedidos")
        df_r["DATA"] = pd.to_datetime(df_r["DATA"], errors="coerce").dt.normalize()
        df_diario = pd.merge(df_diario, df_r, on="DATA", how="outer").fillna(0)
    else:
        df_diario["Total_Expedidos"] = 0

    # 3. Faturamento
    if df_fat_unidades is not None and not df_fat_unidades.empty:
        df_fat_unidades["DATA"] = pd.to_datetime(df_fat_unidades["DATA"], errors="coerce").dt.normalize()
        df_diario = pd.merge(df_diario, df_fat_unidades, on="DATA", how="outer").fillna(0)

    # 4. Frete Terceirizado Agregado por Dia
    if df_frete_tratado is not None and not df_frete_tratado.empty:
        df_frete_agg = (
            df_frete_tratado.groupby("DATA")["Valor Total Frete"]
            .sum()
            .reset_index(name="Total_Frete")
        )
        df_frete_agg["DATA"] = pd.to_datetime(df_frete_agg["DATA"], errors="coerce").dt.normalize()
        df_diario = pd.merge(df_diario, df_frete_agg, on="DATA", how="outer").fillna({"Total_Frete": 0.0})

    if "Total_Frete" not in df_diario.columns:
        df_diario["Total_Frete"] = 0.0

    df_diario = df_diario.dropna(subset=["DATA"]).sort_values("DATA").reset_index(drop=True)
    return df_diario, df_fat_detalhado, df_frete_tratado


def main():
    ui = DashboardUI()
    ui.render_header()

    os.makedirs("./data/", exist_ok=True)
    df_diario, df_fat_detalhado, df_frete_tratado = build_processed_dataset()

    if df_diario is None or df_diario.empty:
        st.info("📂 **Aguardando dados no Back-End:** Insira as planilhas no diretório `./data/` para sincronização.")
        st.stop()

    # -------------------------------------------------------------
    # 📅 FILTRO TEMPORAL GERAL (Faturamento, Produção e KPIs Gerais)
    # -------------------------------------------------------------
    st.subheader("📅 Filtro Temporal Geral (Faturamento & Produção)")
    col_ft1, col_ft2 = st.columns([1.5, 3])

    with col_ft1:
        tipo_filtro = st.radio(
            "Filtrar período por:",
            ["Intervalo de Calendário", "Por Mês", "Por Semana do Ano"],
            horizontal=True,
            key="filtro_tempo_geral_radio",
        )

    min_date = df_diario["DATA"].min().date()
    max_date = df_diario["DATA"].max().date()

    with col_ft2:
        if tipo_filtro == "Intervalo de Calendário":
            data_sel = st.date_input(
                "Selecione o Período:",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date,
                key="filtro_tempo_geral_dates",
            )
            dt_inicio, dt_fim = data_sel if isinstance(data_sel, tuple) and len(data_sel) == 2 else (min_date, max_date)
        elif tipo_filtro == "Por Mês":
            df_diario["Mes_Ano"] = df_diario["DATA"].dt.strftime("%Y-%m")
            meses = sorted(df_diario["Mes_Ano"].unique().tolist())
            mes_sel = st.selectbox("Selecione o Mês:", meses, index=len(meses) - 1, key="filtro_tempo_geral_mes")
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
            semana_sel = st.selectbox("Selecione a Semana:", semanas, index=len(semanas) - 1, key="filtro_tempo_geral_semana")
            dt_inicio = df_diario[df_diario["Semana"] == semana_sel]["DATA"].min().date()
            dt_fim = df_diario[df_diario["Semana"] == semana_sel]["DATA"].max().date()

    # Aplicação do Filtro Temporal Geral
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
    unidade_selecionada = st.selectbox("🏢 Selecione a Unidade / Filial:", opcoes_filiais, index=0, key="unidade_sel_main")

    col_fat_ativa = f"{unidade_selecionada}_Fat"
    col_dev_ativa = f"{unidade_selecionada}_Dev"

    # 1. KPIs Gerais
    render_kpis_gerais(df_filtrado)

    # 2. Seção de Faturamento Monetário
    render_secao_faturamento(df_filtrado, unidade_selecionada)

    # 3. Top Clientes por Faturamento (Posicionado abaixo do Faturamento)
    render_top10_faturamento(df_fat_detalhado, unidade_selecionada)

    # 4. Seção de Produção e Expedição
    render_kpis_medias(df_filtrado, unidade_selecionada)
    render_graficos_producao(df_filtrado, col_fat_ativa, unidade_selecionada)

    # 5. Seção de Frete Terceirizado (Com filtro temporal independente)
    render_secao_frete(df_diario, col_fat_ativa, df_frete_tratado)

    # 6. Tabela Consolidada Operacional
    render_tabela_consolidada(df_filtrado, col_fat_ativa, col_dev_ativa)


if __name__ == "__main__":
    main()