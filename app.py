import os
import pandas as pd
import streamlit as st

from utils.loader import load_all_raw_data_cached
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


@st.cache_data(ttl=3600, show_spinner=False)
def build_processed_dataset():
    """Consolida e pré-computa em memória RAM os DataFrames unificados."""
    (
        df_prod_bruto,
        df_prod_tratado,
        df_rom_tratado,
        df_fat_detalhado,
        df_fat_bruto_raw,
        df_frete_raw,
    ) = load_all_raw_data_cached()

    if df_prod_tratado is None or df_rom_tratado is None:
        return None, None

    df_fat_unidades = parse_faturamento_filiais(df_fat_bruto_raw)

    # 1. Produção
    df_p = df_prod_tratado.copy()
    col_p_data = "DATA" if "DATA" in df_p.columns else df_p.columns[0]
    col_p_qtd = "Quantidade" if "Quantidade" in df_p.columns else df_p.columns[1]

    df_p["DATA"] = pd.to_datetime(df_p[col_p_data], errors="coerce")
    df_p.rename(columns={col_p_qtd: "Total_PVs"}, inplace=True)

    if df_prod_bruto is not None:
        df_pb = df_prod_bruto.copy()
        col_pb_data = "DATA" if "DATA" in df_pb.columns else df_pb.columns[2]
        df_pb["DATA"] = pd.to_datetime(df_pb[col_pb_data], errors="coerce")

        df_status_agg = (
            df_pb.groupby(["DATA", "STATUS"])
            .size()
            .unstack(fill_value=0)
            .reset_index()
            if "STATUS" in df_pb.columns
            else pd.DataFrame(columns=["DATA", "SAUDAVEL", "BACKLOG"])
        )

        for col in ["SAUDAVEL", "BACKLOG"]:
            if col not in df_status_agg.columns:
                df_status_agg[col] = 0

        col_sku = "SKU'S" if "SKU'S" in df_pb.columns else ("SKU" if "SKU" in df_pb.columns else None)
        df_sku_agg = (
            df_pb.groupby("DATA")[col_sku].sum().reset_index(name="Total_SKUs")
            if col_sku
            else pd.DataFrame(columns=["DATA", "Total_SKUs"])
        )

        df_prod_completo = pd.merge(df_sku_agg, df_status_agg, on="DATA", how="outer").fillna(0)
        df_diario = pd.merge(df_p, df_prod_completo, on="DATA", how="left").fillna(0)
    else:
        df_diario = df_p
        df_diario["Total_SKUs"] = 0
        df_diario["SAUDAVEL"] = 0
        df_diario["BACKLOG"] = 0

    # 2. Romaneios
    df_r = df_rom_tratado.copy()
    col_r_data = (
        "Dt. Romaneio"
        if "Dt. Romaneio" in df_r.columns
        else ("DATA" if "DATA" in df_r.columns else df_r.columns[0])
    )
    col_r_qtd = (
        "Qtd. Expedição"
        if "Qtd. Expedição" in df_r.columns
        else ("Quantidade" if "Quantidade" in df_r.columns else df_r.columns[1])
    )

    df_r["DATA"] = pd.to_datetime(df_r[col_r_data], errors="coerce")
    df_r.rename(columns={col_r_qtd: "Total_Expedidos"}, inplace=True)

    df_diario = pd.merge(df_diario, df_r[["DATA", "Total_Expedidos"]], on="DATA", how="outer").fillna(0)

    if not df_fat_unidades.empty:
        df_diario = pd.merge(df_diario, df_fat_unidades, on="DATA", how="outer").fillna(0)

    # 3. Fretes (Merge Left estrito)
    if df_frete_raw is not None and not df_frete_raw.empty:
        df_frete_agg = df_frete_raw.groupby("DATA")["Valor Total Frete"].sum().reset_index(name="Total_Frete")
        df_diario = pd.merge(df_diario, df_frete_agg, on="DATA", how="left").fillna({"Total_Frete": 0.0})
    else:
        df_diario["Total_Frete"] = 0.0

    df_diario = df_diario.dropna(subset=["DATA"]).sort_values("DATA").reset_index(drop=True)
    return df_diario, df_fat_detalhado


def main():
    ui = DashboardUI()
    ui.render_header()

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

    # Aplicação estrita do filtro de datas
    df_filtrado = df_diario[
        (df_diario["DATA"].dt.date >= dt_inicio) & (df_diario["DATA"].dt.date <= dt_fim)
    ].copy().sort_values("DATA").reset_index(drop=True)
    
    df_filtrado["Data_Str"] = df_filtrado["DATA"].dt.strftime("%d/%m")

    # Seletor global de Filial
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

    # Renderização ultrarrápida em cadeia
    render_kpis_gerais(df_filtrado)
    render_secao_faturamento(df_filtrado, unidade_selecionada)
    render_kpis_medias(df_filtrado, unidade_selecionada)
    render_graficos_producao(df_filtrado, col_fat_ativa, unidade_selecionada)
    render_secao_frete(df_filtrado, col_fat_ativa)
    render_top10_faturamento(df_fat_detalhado, unidade_selecionada)
    render_tabela_consolidada(df_filtrado, col_fat_ativa, col_dev_ativa)


if __name__ == "__main__":
    main()