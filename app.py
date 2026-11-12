import os
import pandas as pd
import streamlit as st

from utils.loader import (
    load_treated_data_cached,
    load_dados_sla,
)
from utils.parser import parse_faturamento_filiais
from components.ui_config import DashboardUI
from components.kpis import render_kpis_gerais, render_kpis_medias
from components.charts_faturamento import render_secao_faturamento
from components.charts_producao import render_graficos_producao
from components.charts_frete import render_secao_frete
from components.tables import render_top10_faturamento, render_tabela_consolidada
from components.sla_farol import render_secao_sla

st.set_page_config(
    page_title="Dashboard Operacional & BI",
    page_icon="📦",
    layout="wide",
)


def get_local_files_signature() -> str:
    """Gera assinatura local dos arquivos para atualizar o cache automaticamente."""
    sigs = []
    for folder in ["./data/", "."]:
        if os.path.exists(folder):
            for fname in sorted(os.listdir(folder)):
                if fname.lower().endswith((".xlsx", ".xls", ".csv")) and not fname.startswith("~$"):
                    fp = os.path.join(folder, fname)
                    sigs.append(f"{fp}:{os.path.getmtime(fp)}:{os.path.getsize(fp)}")
    return "|".join(sigs)


def _render_filtro_temporal_isolado(df_base: pd.DataFrame, titulo: str, key_prefix: str) -> pd.DataFrame:
    """Renderiza filtro temporal independente (Calendário, Mês ou Semana) para uma aba específica."""
    st.subheader(titulo)

    if df_base is None or df_base.empty:
        return pd.DataFrame()

    df_work = df_base.copy()
    df_work["DATA"] = pd.to_datetime(df_work["DATA"], errors="coerce").dt.normalize()
    df_work = df_work.dropna(subset=["DATA"]).sort_values("DATA").reset_index(drop=True)

    col_ft1, col_ft2 = st.columns([1.5, 3])

    with col_ft1:
        tipo_filtro = st.radio(
            "Filtrar período por:",
            ["Intervalo de Calendário", "Por Mês", "Por Semana do Ano"],
            horizontal=True,
            key=f"{key_prefix}_radio",
        )

    min_date = df_work["DATA"].min().date()
    max_date = df_work["DATA"].max().date()

    with col_ft2:
        if tipo_filtro == "Intervalo de Calendário":
            data_sel = st.date_input(
                "Selecione o Período:",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date,
                key=f"{key_prefix}_dates",
            )
            dt_inicio, dt_fim = data_sel if isinstance(data_sel, tuple) and len(data_sel) == 2 else (min_date, max_date)

        elif tipo_filtro == "Por Mês":
            df_work["Mes_Ano"] = df_work["DATA"].dt.strftime("%Y-%m")
            meses = sorted(df_work["Mes_Ano"].unique().tolist())
            mes_sel = st.selectbox("Selecione o Mês:", meses, index=len(meses) - 1, key=f"{key_prefix}_mes")
            dt_inicio = df_work[df_work["Mes_Ano"] == mes_sel]["DATA"].min().date()
            dt_fim = df_work[df_work["Mes_Ano"] == mes_sel]["DATA"].max().date()

        else:
            df_work["Semana_Inicio"] = df_work["DATA"].apply(lambda d: d - pd.Timedelta(days=d.weekday()))
            df_work["Semana_Fim"] = df_work["Semana_Inicio"] + pd.Timedelta(days=6)

            df_work["Semana_Label"] = (
                "Semana do dia "
                + df_work["Semana_Inicio"].dt.strftime("%d/%m")
                + " - "
                + df_work["Semana_Fim"].dt.strftime("%d/%m")
            )

            df_semanas_ord = df_work.sort_values("Semana_Inicio")
            semanas = df_semanas_ord["Semana_Label"].unique().tolist()

            semana_sel = st.selectbox(
                "Selecione a Semana:",
                semanas,
                index=len(semanas) - 1,
                key=f"{key_prefix}_semana",
            )

            dt_inicio = df_work[df_work["Semana_Label"] == semana_sel]["DATA"].min().date()
            dt_fim = df_work[df_work["Semana_Label"] == semana_sel]["DATA"].max().date()

    df_out = df_work[
        (df_work["DATA"].dt.date >= dt_inicio) & (df_work["DATA"].dt.date <= dt_fim)
    ].copy().sort_values("DATA").reset_index(drop=True)

    df_out = df_out[df_out["DATA"].dt.strftime("%d/%m") != "02/01"].reset_index(drop=True)
    df_out["Data_Str"] = df_out["DATA"].dt.strftime("%d/%m")
    return df_out


@st.cache_data(ttl=60, show_spinner=False)
def build_processed_dataset(_sig: str = ""):
    """Unifica os dados de Produção, Romaneios, Faturamento e Frete."""
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

    renames = {}
    for c in df_diario.columns:
        c_upper = str(c).strip().upper()
        if c_upper == "QUANTIDADE":
            renames[c] = "Total_PVs"
        elif c_upper == "SAUDAVEL":
            renames[c] = "Saudavel"
        elif c_upper == "BACKLOG":
            renames[c] = "Backlog"
        elif c_upper in ["SKU'S", "SKUS", "TOTAL_SKUS"]:
            renames[c] = "Total_SKUs"

    if renames:
        df_diario.rename(columns=renames, inplace=True)

    df_diario["DATA"] = pd.to_datetime(df_diario["DATA"], errors="coerce").dt.normalize()

    # 2. Romaneios / Expedição
    if df_rom_tratado is not None and not df_rom_tratado.empty:
        col_exp = "Qtd. Expedição" if "Qtd. Expedição" in df_rom_tratado.columns else df_rom_tratado.columns[1]
        df_r = df_rom_tratado.groupby("DATA")[col_exp].sum().reset_index(name="Total_Expedidos")
        df_r["DATA"] = pd.to_datetime(df_r["DATA"], errors="coerce").dt.normalize()
        df_diario = pd.merge(df_diario, df_r, on="DATA", how="outer")
    else:
        df_diario["Total_Expedidos"] = 0

    # 3. Faturamento
    if df_fat_unidades is not None and not df_fat_unidades.empty:
        df_fat_unidades["DATA"] = pd.to_datetime(df_fat_unidades["DATA"], errors="coerce").dt.normalize()
        df_diario = pd.merge(df_diario, df_fat_unidades, on="DATA", how="outer")

    # 4. Frete Terceirizado
    if df_frete_tratado is not None and not df_frete_tratado.empty:
        df_frete_agg = (
            df_frete_tratado.groupby("DATA")["Valor Total Frete"]
            .sum()
            .reset_index(name="Total_Frete")
        )
        df_frete_agg["DATA"] = pd.to_datetime(df_frete_agg["DATA"], errors="coerce").dt.normalize()
        df_diario = pd.merge(df_diario, df_frete_agg, on="DATA", how="outer")

    # Preenchimento numérico pós-merge
    colunas_num = df_diario.select_dtypes(include=["number", "float64", "int64"]).columns
    df_diario[colunas_num] = df_diario[colunas_num].fillna(0.0)

    if "Notas_Realizadas" not in df_diario.columns:
        df_diario["Notas_Realizadas"] = df_diario["Total_PVs"]

    df_diario["SAUDAVEL"] = df_diario["Saudavel"]
    df_diario["BACKLOG"] = df_diario["Backlog"]

    df_diario = df_diario.dropna(subset=["DATA"]).sort_values("DATA").reset_index(drop=True)
    return df_diario, df_fat_detalhado, df_frete_tratado


def main():
    ui = DashboardUI()
    ui.render_header()

    os.makedirs("./data/", exist_ok=True)
    sig = get_local_files_signature()
    df_diario, df_fat_detalhado, df_frete_tratado = build_processed_dataset(sig)
    df_sla = load_dados_sla(sig)

    if df_diario is None or df_diario.empty:
        st.info("📂 **Aguardando dados no Back-End:** Insira as planilhas no diretório `./data/` para sincronização.")
        st.stop()

    # =========================================================================
    # 🗂️ ORGANIZAÇÃO EM ABAS ESPECÍFICAS (CADA ABA COM SEUS PRÓPRIOS FILTROS)
    # =========================================================================
    tab_fat, tab_prod, tab_frete, tab_sla, tab_tabela = st.tabs([
        "💰 Faturamento & Clientes",
        "🏭 Produção & Expedição",
        "🚚 Gestão & Custo de Frete",
        "🚦 Farol SLA & Operação",
        "📜 Base Consolidada",
    ])

    # -------------------------------------------------------------------------
    # ABA 1: FATURAMENTO & CLIENTES (FILTRO TEMPORAL E FILIAL ISOLADOS)
    # -------------------------------------------------------------------------
    with tab_fat:
        df_filtrado_fat = _render_filtro_temporal_isolado(
            df_diario,
            "📅 Filtro Temporal — Faturamento & Clientes",
            key_prefix="filtro_tempo_fat",
        )

        opcoes_filiais = [
            "Todas as Unidades (Geral)",
            "0101 - Matriz",
            "0102 - Filial RJ",
            "0103 - Filial CP",
            "0104 - Filial SBC",
        ]
        unidade_selecionada = st.selectbox(
            "🏢 Selecione a Unidade / Filial (Exclusivo Faturamento):",
            opcoes_filiais,
            index=0,
            key="unidade_sel_fat_isolado",
        )

        render_kpis_gerais(df_filtrado_fat, unidade_selecionada)
        render_secao_faturamento(df_filtrado_fat, unidade_selecionada)
        render_top10_faturamento(df_fat_detalhado, unidade_selecionada)

    # -------------------------------------------------------------------------
    # ABA 2: PRODUÇÃO & EXPEDIÇÃO (FILTRO TEMPORAL ISOLADO A PARTIR DE 07/10)
    # -------------------------------------------------------------------------
    with tab_prod:
        mask_prod_real = (
            (df_diario.get("Notas_Realizadas", 0) > 0)
            | (df_diario.get("Saudavel", 0) > 0)
            | (df_diario.get("Backlog", 0) > 0)
            | (df_diario.get("Total_Expedidos", 0) > 0)
        )
        df_base_prod = (
            df_diario[df_diario["DATA"] >= df_diario.loc[mask_prod_real, "DATA"].min()].copy()
            if mask_prod_real.any()
            else df_diario.copy()
        )

        df_filtrado_prod = _render_filtro_temporal_isolado(
            df_base_prod,
            "📅 Filtro Temporal — Produção & Expedição",
            key_prefix="filtro_tempo_prod",
        )

        render_kpis_medias(df_filtrado_prod, "Todas as Unidades (Geral)")
        render_graficos_producao(df_filtrado_prod, "Todas as Unidades (Geral)_Fat", "Todas as Unidades (Geral)")

    # -------------------------------------------------------------------------
    # ABA 3: GESTÃO & CUSTO DE FRETE
    # -------------------------------------------------------------------------
    with tab_frete:
        render_secao_frete(df_diario, "Todas as Unidades (Geral)_Fat", df_frete_tratado)

    # -------------------------------------------------------------------------
    # ABA 4: FAROL SLA & OPERAÇÃO
    # -------------------------------------------------------------------------
    with tab_sla:
        render_secao_sla(df_sla)

    # -------------------------------------------------------------------------
    # ABA 5: BASE CONSOLIDADA
    # -------------------------------------------------------------------------
    with tab_tabela:
        df_base_tab = df_diario.copy()
        df_base_tab["Data_Str"] = df_base_tab["DATA"].dt.strftime("%d/%m")
        render_tabela_consolidada(
            df_base_tab,
            "Todas as Unidades (Geral)_Fat",
            "Todas as Unidades (Geral)_Dev",
        )


if __name__ == "__main__":
    main()