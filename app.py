import io
import os
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Tratamento seguro da biblioteca cryptography (evita ModuleNotFoundError)
try:
    from cryptography.fernet import Fernet
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False

# Configuração da página
st.set_page_config(
    page_title="Dashboard Operacional & BI - Higimed",
    page_icon="📦",
    layout="wide",
)


# ==========================================
# 1. GERENCIADOR DE SEGURANÇA E CRIPTOGRAFIA
# ==========================================
class DataSecurityManager:
    """Gerencia a leitura segura de arquivos criptografados em memória no back-end."""

    @staticmethod
    def load_encrypted_excel(encrypted_path: str, key: bytes, sheet_name=0) -> pd.DataFrame:
        if not HAS_CRYPTO or not os.path.exists(encrypted_path):
            return None
        f = Fernet(key)
        with open(encrypted_path, "rb") as file:
            encrypted_data = file.read()
        decrypted_data = f.decrypt(encrypted_data)
        return pd.read_excel(io.BytesIO(decrypted_data), sheet_name=sheet_name)


# ==========================================
# 2. CARREGAMENTO SEMIAUTOMÁTICO (BACK-END)
# ==========================================
class DataLoader:
    """Lê as planilhas diretamente do diretório back-end ./data/ ou da raiz."""

    DATA_DIR = "./data/"

    def __init__(self, key: bytes = None):
        self.key = key

    def read_dataframe(self, filename: str, sheet_name=0, header=0) -> pd.DataFrame:
        path = os.path.join(self.DATA_DIR, filename)
        enc_path = path + ".enc"

        # 1. Tenta versão criptografada
        if self.key and os.path.exists(enc_path):
            try:
                return DataSecurityManager.load_encrypted_excel(enc_path, self.key, sheet_name)
            except Exception:
                pass

        # 2. Leitura direta no diretório ./data/
        if os.path.exists(path):
            try:
                return pd.read_excel(path, sheet_name=sheet_name, header=header)
            except Exception:
                try:
                    return pd.read_excel(path, sheet_name=0, header=header)
                except Exception:
                    return None

        # 3. Fallback para a raiz do projeto
        if os.path.exists(filename):
            try:
                return pd.read_excel(filename, sheet_name=sheet_name, header=header)
            except Exception:
                try:
                    return pd.read_excel(filename, sheet_name=0, header=header)
                except Exception:
                    return None

        return None

    def load_all_data(self):
        # Produção
        df_prod_bruto = self.read_dataframe("DadosProducao.xlsx", "DadosBrutos")
        df_prod_tratado = self.read_dataframe("DadosProducao.xlsx", "LimpezaDados")

        # Romaneios
        df_rom_tratado = self.read_dataframe("DadosRomaneios.xlsx", "DadosRomaneios")
        if df_rom_tratado is None:
            df_rom_tratado = self.read_dataframe("DadosRomaneios.xlsx", "Planilha1")

        # Faturamento por cliente (Detalhamento)
        df_fat_detalhado = self.read_dataframe("DadosFaturamento.xlsx", "Faturamento por cliente")
        if df_fat_detalhado is None:
            df_fat_detalhado = self.read_dataframe("DadosFaturamento.xlsx", 0)

        # Faturamento Bruto Diário com Filiais (Aba FaturamentoBruto)
        df_fat_bruto_raw = self.read_dataframe("DadosFaturamento.xlsx", "FaturamentoBruto", header=None)

        return (
            df_prod_bruto,
            df_prod_tratado,
            df_rom_tratado,
            df_fat_detalhado,
            df_fat_bruto_raw,
        )


# ==========================================
# 3. INTERFACE E RENDERIZAÇÃO (STREAMLIT)
# ==========================================
class DashboardUI:

    def __init__(self):
        self.setup_css()

    def setup_css(self):
        st.markdown(
            """
            <style>
            .main { background-color: #f8f9fa; color: #000000 !important; }
            h1, h2, h3, h4, h5, h6 { color: #000000 !important; font-weight: 800 !important; }
            p, span, label, div, .stMarkdown { color: #000000 !important; font-weight: 600; }
            [data-testid="stMetric"] {
                background-color: #ffffff; padding: 15px; border-radius: 10px;
                border: 2px solid #ced4da; box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }
            [data-testid="stMetricLabel"] { color: #000000 !important; font-weight: 700 !important; }
            [data-testid="stMetricValue"] { color: #000000 !important; font-weight: 800 !important; }
            </style>
        """,
            unsafe_allow_html=True,
        )

    def render_header(self):
        col_logo1, col_titulo, col_logo2 = st.columns([1.2, 3.6, 1.2])
        
        with col_logo1:
            # Tenta carregar logo PNG transparente (logo.png ou images.jpg)
            if os.path.exists("logo.png"):
                st.image("logo.png", width=110)
            elif os.path.exists("images.jpg"):
                st.image("images.jpg", width=110)
            else:
                st.write("Control Log")

        with col_titulo:
            st.title("Dashboard de Produção, Expedição & BI")
            st.markdown("Monitoramento e consolidação de dados via **Back-End Seguro**.")

        with col_logo2:
            # Tenta carregar logo2.png sem caixa branca em volta
            if os.path.exists("logo2.png"):
                st.image("logo2.png", width=130)
            else:
                st.write("Higimed")
                
        st.divider()


# ==========================================
# 4. TRATAMENTO DE DADOS DE FATURAMENTO POR FILIAL
# ==========================================
def parse_faturamento_filiais(df_raw):
    """Trata a estrutura multi-colunas da aba FaturamentoBruto."""
    if df_raw is None or df_raw.empty:
        return pd.DataFrame()

    # Estrutura identificada:
    # Linha 1 (índice 1): Datas na Coluna 1; Matriz Fat (Col 2); Filial RJ Fat (Col 4); Filial CP Fat (Col 6); Filial SBC Fat (Col 8); Total (Col 9)
    df_data = df_raw.iloc[1:].copy()
    
    col_data = df_data.iloc[:, 1]
    col_matriz = pd.to_numeric(df_data.iloc[:, 2], errors="coerce").fillna(0)
    col_rj = pd.to_numeric(df_data.iloc[:, 4], errors="coerce").fillna(0)
    col_cp = pd.to_numeric(df_data.iloc[:, 6], errors="coerce").fillna(0)
    col_sbc = pd.to_numeric(df_data.iloc[:, 8], errors="coerce").fillna(0)
    col_tot = pd.to_numeric(df_data.iloc[:, 9], errors="coerce").fillna(0)

    df_fat = pd.DataFrame({
        "DATA": pd.to_datetime(col_data, errors="coerce"),
        "0101 - Matriz": col_matriz,
        "0102 - Filial RJ": col_rj,
        "0103 - Filial CP": col_cp,
        "0104 - Filial SBC": col_sbc,
        "Todas as Unidades (Geral)": col_tot
    }).dropna(subset=["DATA"]).sort_values("DATA").reset_index(drop=True)

    return df_fat


# ==========================================
# 5. EXECUÇÃO PRINCIPAL DO DASHBOARD
# ==========================================
def main():
    ui = DashboardUI()
    ui.render_header()

    os.makedirs("./data/", exist_ok=True)
    loader = DataLoader()
    (
        df_prod_bruto,
        df_prod_tratado,
        df_rom_tratado,
        df_fat_detalhado,
        df_fat_bruto_raw,
    ) = loader.load_all_data()

    if df_prod_tratado is None or df_rom_tratado is None:
        st.info(
            "📂 **Aguardando dados no Back-End:** Insira as planilhas"
            " (`DadosProducao.xlsx`, `DadosRomaneios.xlsx` e"
            " `DadosFaturamento.xlsx`) no diretório `./data/` para sincronização"
            " automática."
        )
        st.stop()

    # --- PROCESSAMENTO DO FATURAMENTO BRUTO POR FILIAIS ---
    df_fat_unidades = parse_faturamento_filiais(df_fat_bruto_raw)

    # --- FILTRO SELETOR DE FILIAIS / MATRIZ ---
    col_filial_sel, col_space = st.columns([2, 2])
    with col_filial_sel:
        opcoes_filiais = [
            "Todas as Unidades (Geral)",
            "0101 - Matriz",
            "0102 - Filial RJ",
            "0103 - Filial CP",
            "0104 - Filial SBC"
        ]
        unidade_selecionada = st.selectbox(
            "🏢 Selecione a Unidade / Filial para Análise:",
            opcoes_filiais,
            index=0,
            key="seletor_unidade_filial"
        )

    # --- TRATAMENTO DE PRODUÇÃO ---
    df_p = df_prod_tratado.copy()
    col_p_data = "DATA" if "DATA" in df_p.columns else df_p.columns[0]
    col_p_qtd = "Quantidade" if "Quantidade" in df_p.columns else df_p.columns[1]

    df_p["DATA"] = pd.to_datetime(df_p[col_p_data], errors="coerce")
    df_p.rename(columns={col_p_qtd: "Total_PVs"}, inplace=True)

    if df_prod_bruto is not None:
        df_pb = df_prod_bruto.copy()
        col_pb_data = "DATA" if "DATA" in df_pb.columns else df_pb.columns[2]
        df_pb["DATA"] = pd.to_datetime(df_pb[col_pb_data], errors="coerce")

        if "STATUS" in df_pb.columns:
            df_status_agg = (
                df_pb.groupby(["DATA", "STATUS"])
                .size()
                .unstack(fill_value=0)
                .reset_index()
            )
        else:
            df_status_agg = pd.DataFrame(columns=["DATA", "SAUDAVEL", "BACKLOG"])

        if "SAUDAVEL" not in df_status_agg.columns:
            df_status_agg["SAUDAVEL"] = 0
        if "BACKLOG" not in df_status_agg.columns:
            df_status_agg["BACKLOG"] = 0

        col_sku = (
            "SKU'S"
            if "SKU'S" in df_pb.columns
            else ("SKU" if "SKU" in df_pb.columns else None)
        )
        if col_sku:
            df_sku_agg = (
                df_pb.groupby("DATA")[col_sku].sum().reset_index(name="Total_SKUs")
            )
        else:
            df_sku_agg = pd.DataFrame(columns=["DATA", "Total_SKUs"])

        df_prod_completo = pd.merge(df_sku_agg, df_status_agg, on="DATA", how="outer").fillna(0)
        df_diario = pd.merge(df_p, df_prod_completo, on="DATA", how="left").fillna(0)
    else:
        df_diario = df_p
        df_diario["Total_SKUs"] = 0
        df_diario["SAUDAVEL"] = 0
        df_diario["BACKLOG"] = 0

    # --- TRATAMENTO DE ROMANEIOS ---
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

    df_diario = pd.merge(
        df_diario, df_r[["DATA", "Total_Expedidos"]], on="DATA", how="outer"
    ).fillna(0)

    # --- ANEXA O FATURAMENTO DA UNIDADE SELECIONADA ---
    if not df_fat_unidades.empty and unidade_selecionada in df_fat_unidades.columns:
        df_fat_sub = df_fat_unidades[["DATA", unidade_selecionada]].rename(
            columns={unidade_selecionada: "Valor_Faturado"}
        )
        df_diario = pd.merge(df_diario, df_fat_sub, on="DATA", how="left").fillna(0)
    else:
        df_diario["Valor_Faturado"] = 0.0

    df_diario = df_diario.sort_values("DATA").reset_index(drop=True)

    # Layout padrão Plotly
    layout_graficos = dict(
        template="plotly_white",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#000000", size=13, family="Arial"),
        margin=dict(l=40, r=40, t=50, b=40),
    )

    # ==========================================
    # PRIMEIRA PARTE: GRÁFICO ISOLADO DE FATURAMENTO
    # ==========================================
    st.subheader(f"💰 Faturamento Diário - {unidade_selecionada}")

    if not df_diario.empty:
        df_fat_diario_plot = df_diario[["DATA", "Valor_Faturado"]].copy()
        df_fat_diario_plot["Data_Str"] = df_fat_diario_plot["DATA"].dt.strftime("%Y-%m-%d")

        col_fat_f1, col_fat_f2 = st.columns([1.5, 3])

        with col_fat_f1:
            tipo_filtro_fat = st.radio(
                "Filtrar Faturamento por:",
                ["Período Completo", "Intervalo de Calendário", "Por Mês"],
                horizontal=True,
                key="filtro_fatur_exclusivo",
            )

        min_f_date = df_fat_diario_plot["DATA"].min().date()
        max_f_date = df_fat_diario_plot["DATA"].max().date()

        with col_fat_f2:
            if tipo_filtro_fat == "Intervalo de Calendário":
                d_fat_sel = st.date_input(
                    "Selecione o Intervalo de Faturamento:",
                    value=(min_f_date, max_f_date),
                    min_value=min_f_date,
                    max_value=max_f_date,
                    key="date_fat_input",
                )
                if isinstance(d_fat_sel, tuple) and len(d_fat_sel) == 2:
                    dt_fat_i, dt_fat_f = d_fat_sel
                else:
                    dt_fat_i, dt_fat_f = min_f_date, max_f_date
            elif tipo_filtro_fat == "Por Mês":
                df_fat_diario_plot["Mes_Ano"] = df_fat_diario_plot["DATA"].dt.strftime("%Y-%m")
                meses_fat = df_fat_diario_plot["Mes_Ano"].unique().tolist()
                mes_fat_sel = st.selectbox(
                    "Selecione o Mês:",
                    meses_fat,
                    index=len(meses_fat) - 1,
                    key="mes_fat_sel",
                )
                dt_fat_i = df_fat_diario_plot[df_fat_diario_plot["Mes_Ano"] == mes_fat_sel]["DATA"].min().date()
                dt_fat_f = df_fat_diario_plot[df_fat_diario_plot["Mes_Ano"] == mes_fat_sel]["DATA"].max().date()
            else:
                dt_fat_i, dt_fat_f = min_f_date, max_f_date

        df_fat_exclusivo = df_fat_diario_plot[
            (df_fat_diario_plot["DATA"].dt.date >= dt_fat_i)
            & (df_fat_diario_plot["DATA"].dt.date <= dt_fat_f)
        ].copy()

        labels_fat_solo = [
            f"<b>R$ {v:,.0f}</b>".replace(",", ".")
            for v in df_fat_exclusivo["Valor_Faturado"]
        ]

        fig_fat_solo = go.Figure()
        fig_fat_solo.add_trace(
            go.Bar(
                x=df_fat_exclusivo["Data_Str"],
                y=df_fat_exclusivo["Valor_Faturado"],
                name=f"Faturamento ({unidade_selecionada})",
                marker=dict(color="#2ec4b6", line=dict(color="#000000", width=1)),
                text=labels_fat_solo,
                textfont=dict(color="#000000", size=11),
                textposition="outside",
                cliponaxis=False,
            )
        )
        fig_fat_solo.update_layout(**layout_graficos)
        fig_fat_solo.update_layout(
            yaxis=dict(title="<b>Valor Faturado (R$)</b>"),
            xaxis=dict(title="<b>Data de Emissão</b>"),
        )
        st.plotly_chart(fig_fat_solo, use_container_width=True)

        total_fat_bruto_periodo = df_fat_exclusivo["Valor_Faturado"].sum()
        qtd_dias_faturados = len(df_fat_exclusivo[df_fat_exclusivo["Valor_Faturado"] > 0])
        media_fat_diaria = (
            total_fat_bruto_periodo / qtd_dias_faturados
            if qtd_dias_faturados > 0
            else 0.0
        )

        col_tf1, col_tf2, col_tf3 = st.columns(3)
        col_tf1.metric(
            f"💵 Total Faturado ({unidade_selecionada})",
            f"R$ {total_fat_bruto_periodo:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        )
        col_tf2.metric("📅 Dias com Faturamento", f"{qtd_dias_faturados} dias")
        col_tf3.metric(
            "📊 Média Diária Faturada",
            f"R$ {media_fat_diaria:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        )

    st.divider()

    # --- SELEÇÃO TEMPORAL GERAL DA OPERAÇÃO ---
    st.subheader("📅 Filtro Temporal de Análise Operacional")
    col_ft1, col_ft2 = st.columns([1.5, 3])

    with col_ft1:
        tipo_filtro = st.radio(
            "Filtrar período por:",
            ["Intervalo de Calendário", "Por Mês", "Por Semana do Ano"],
            horizontal=True,
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
            )
            if isinstance(data_sel, tuple) and len(data_sel) == 2:
                dt_inicio, dt_fim = data_sel
            else:
                dt_inicio, dt_fim = min_date, max_date

        elif tipo_filtro == "Por Mês":
            df_diario["Mes_Ano"] = df_diario["DATA"].dt.strftime("%Y-%m")
            meses = df_diario["Mes_Ano"].unique().tolist()
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

    df_filtrado = df_diario[
        (df_diario["DATA"].dt.date >= dt_inicio)
        & (df_diario["DATA"].dt.date <= dt_fim)
    ].copy()
    df_filtrado["Data_Str"] = df_filtrado["DATA"].dt.strftime("%Y-%m-%d")

    st.divider()

    # --- EXPORTAÇÃO DOS DADOS PARA EXCEL ---
    col_exp1, col_exp2 = st.columns([3, 1])
    with col_exp2:
        output_buffer = io.BytesIO()
        with pd.ExcelWriter(output_buffer, engine="xlsxwriter") as writer:
            df_filtrado.to_excel(writer, sheet_name="Dados_Consolidados", index=False)

        st.download_button(
            label="📥 Exportar Dados para Excel",
            data=output_buffer.getvalue(),
            file_name=f"Consolidado_BI_{dt_inicio}_a_{dt_fim}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    # --- KPIs PRINCIPAIS ---
    k1, k2, k3, k4, k5 = st.columns(5)
    total_pvs = int(df_filtrado["Total_PVs"].sum())
    total_saudavel = int(df_filtrado["SAUDAVEL"].sum())
    total_backlog = int(df_filtrado["BACKLOG"].sum())
    total_skus = int(df_filtrado["Total_SKUs"].sum())
    total_fat = df_filtrado["Valor_Faturado"].sum()

    k1.metric("📄 Total PVs", total_pvs)
    k2.metric("✅ Saudável", total_saudavel)
    k3.metric("⚠️ Backlog", total_backlog)
    k4.metric("📦 Total SKUs", total_skus)
    k5.metric(
        "💰 Faturamento Total",
        f"R$ {total_fat:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
    )

    # --- GRÁFICO 1: PRODUÇÃO VS FATURAMENTO ---
    st.subheader(f"💵 Produção Diária: Pedidos de Venda (PV) vs. Faturamento ({unidade_selecionada})")
    fig_fat = go.Figure()
    fig_fat.add_trace(
        go.Bar(
            x=df_filtrado["Data_Str"],
            y=df_filtrado["Total_PVs"],
            name="PVs",
            marker=dict(color="#0077b6", line=dict(color="#000000", width=1)),
            text=[f"<b>{int(v)}</b>" for v in df_filtrado["Total_PVs"]],
            textfont=dict(color="#ffffff", size=13),
            textposition="auto",
        )
    )
    fig_fat.add_trace(
        go.Scatter(
            x=df_filtrado["Data_Str"],
            y=df_filtrado["Valor_Faturado"],
            name="Faturamento",
            mode="lines+markers+text",
            text=[f"<b>R$ {v:,.0f}</b>".replace(",", ".") for v in df_filtrado["Valor_Faturado"]],
            textfont=dict(color="#000000", size=12),
            textposition="top center",
            marker=dict(color="#2ec4b6", size=8),
            line=dict(color="#2ec4b6", width=3),
            yaxis="y2",
        )
    )
    fig_fat.update_layout(**layout_graficos)
    fig_fat.update_layout(
        yaxis=dict(title="<b>Qtd. Pedidos (PV)</b>"),
        yaxis2=dict(
            title="<b>Valor Faturado (R$)</b>",
            overlaying="y",
            side="right",
            showgrid=False,
        ),
    )
    st.plotly_chart(fig_fat, use_container_width=True)

    # --- GRÁFICO 2: PRODUÇÃO VS SKUs ---
    st.subheader("📊 Produção Diária: Pedidos de Venda (PV) vs. SKUs")
    fig_sku = go.Figure()
    fig_sku.add_trace(
        go.Bar(
            x=df_filtrado["Data_Str"],
            y=df_filtrado["Total_PVs"],
            name="PVs",
            marker=dict(color="#0077b6", line=dict(color="#000000", width=1)),
            text=[f"<b>{int(v)}</b>" for v in df_filtrado["Total_PVs"]],
            textfont=dict(color="#ffffff", size=13),
            textposition="auto",
        )
    )
    fig_sku.add_trace(
        go.Scatter(
            x=df_filtrado["Data_Str"],
            y=df_filtrado["Total_SKUs"],
            name="SKUs",
            mode="lines+markers+text",
            text=[f"<b>{int(v)}</b>" for v in df_filtrado["Total_SKUs"]],
            textfont=dict(color="#000000", size=12),
            textposition="top center",
            marker=dict(color="#d97706", size=8),
            line=dict(color="#d97706", width=3),
            yaxis="y2",
        )
    )
    fig_sku.update_layout(**layout_graficos)
    fig_sku.update_layout(
        yaxis=dict(title="<b>Qtd. Pedidos (PV)</b>"),
        yaxis2=dict(
            title="<b>Total SKUs</b>",
            overlaying="y",
            side="right",
            showgrid=False,
        ),
    )
    st.plotly_chart(fig_sku, use_container_width=True)

    # --- GRÁFICO 3: SAUDÁVEL VS BACKLOG ---
    st.subheader("📋 Produção Diária Isolada: Notas Saudáveis vs. Backlog")
    fig_status = go.Figure()
    fig_status.add_trace(
        go.Bar(
            x=df_filtrado["Data_Str"],
            y=df_filtrado["SAUDAVEL"],
            name="Notas Saudáveis",
            marker=dict(color="#0f9f90", line=dict(color="#000000", width=1)),
            text=[f"<b>{int(v)}</b>" if v > 0 else "" for v in df_filtrado["SAUDAVEL"]],
            textfont=dict(color="#ffffff", size=12),
            textposition="auto",
        )
    )
    fig_status.add_trace(
        go.Bar(
            x=df_filtrado["Data_Str"],
            y=df_filtrado["BACKLOG"],
            name="Backlog",
            marker=dict(color="#d9381e", line=dict(color="#000000", width=1)),
            text=[f"<b>{int(v)}</b>" if v > 0 else "" for v in df_filtrado["BACKLOG"]],
            textfont=dict(color="#ffffff", size=12),
            textposition="auto",
        )
    )
    fig_status.update_layout(**layout_graficos)
    fig_status.update_layout(
        barmode="stack", yaxis=dict(title="<b>Quantidade de Pedidos (PV)</b>")
    )
    st.plotly_chart(fig_status, use_container_width=True)

    # --- GRÁFICO 4: PRODUÇÃO VS EXPEDIÇÃO (ROMANEIOS) ---
    st.subheader("🚚 Comparativo: Pedidos Produzidos (PV) vs. Expedições")
    fig_comp = go.Figure()
    fig_comp.add_trace(
        go.Bar(
            x=df_filtrado["Data_Str"],
            y=df_filtrado["Total_PVs"],
            name="Produzidos no Dia",
            marker=dict(color="#0f9f90", line=dict(color="#000000", width=1)),
            text=[f"<b>{int(v)}</b>" for v in df_filtrado["Total_PVs"]],
            textfont=dict(color="#ffffff", size=12),
            textposition="auto",
        )
    )
    fig_comp.add_trace(
        go.Bar(
            x=df_filtrado["Data_Str"],
            y=df_filtrado["Total_Expedidos"],
            name="Expedidos no Dia (Romaneio)",
            marker=dict(color="#d9381e", line=dict(color="#000000", width=1)),
            text=[f"<b>{int(v)}</b>" for v in df_filtrado["Total_Expedidos"]],
            textfont=dict(color="#ffffff", size=12),
            textposition="auto",
        )
    )
    fig_comp.update_layout(**layout_graficos)
    fig_comp.update_layout(barmode="group", yaxis=dict(title="<b>Quantidade</b>"))
    st.plotly_chart(fig_comp, use_container_width=True)

    # --- RANKING TOP 5 PVS POR CLIENTE ---
    st.divider()
    st.subheader("🏆 Top 5 Clientes por Pedidos de Venda (PVs Produzidos)")

    if (
        df_prod_bruto is not None
        and "CLIENTE" in df_prod_bruto.columns
        and "PV" in df_prod_bruto.columns
    ):
        df_pb_cliente = df_prod_bruto.copy()
        col_pb_dt = "DATA" if "DATA" in df_pb_cliente.columns else df_pb_cliente.columns[2]
        df_pb_cliente["DATA_STR"] = pd.to_datetime(
            df_pb_cliente[col_pb_dt], errors="coerce"
        ).dt.strftime("%Y-%m-%d")
        datas_p_disp = sorted(df_pb_cliente["DATA_STR"].dropna().unique())

        col_m_pv, col_d_pv = st.columns([2, 2])
        with col_m_pv:
            modo_top5_pv = st.radio(
                "Modo de Exibição do Top 5 PVs:",
                ["Por Dia Selecionado", "Acumulado do Período Geral"],
                horizontal=True,
                key="modo_top5_pv",
            )

        if modo_top5_pv == "Por Dia Selecionado":
            with col_d_pv:
                data_p_sel = st.selectbox(
                    "Selecione a Data para visualizar o Top 5 PVs:",
                    datas_p_disp,
                    index=len(datas_p_disp) - 1,
                    key="sel_top5_pv_date",
                )
            df_top5_pv_filtrado = df_pb_cliente[df_pb_cliente["DATA_STR"] == data_p_sel]
            titulo_top5_pv = f"Top 5 Clientes por PVs no Dia: {data_p_sel}"
        else:
            df_top5_pv_filtrado = df_pb_cliente
            titulo_top5_pv = "Top 5 Clientes por PVs Acumulado no Período"

        df_ranking_pv = (
            df_top5_pv_filtrado.groupby("CLIENTE")["PV"]
            .nunique()
            .reset_index(name="Qtd_PVs")
            .sort_values("Qtd_PVs", ascending=False)
            .head(5)
        )
        df_ranking_pv = df_ranking_pv.sort_values("Qtd_PVs", ascending=True)

        if not df_ranking_pv.empty:
            fig_top_pv = go.Figure()
            fig_top_pv.add_trace(
                go.Bar(
                    y=df_ranking_pv["CLIENTE"],
                    x=df_ranking_pv["Qtd_PVs"],
                    orientation="h",
                    marker=dict(color="#3a86ff", line=dict(color="#000000", width=1)),
                    text=[f"<b>{int(v)} PVs</b>" for v in df_ranking_pv["Qtd_PVs"]],
                    textfont=dict(color="#ffffff", size=12),
                    textposition="auto",
                )
            )
            fig_top_pv.update_layout(**layout_graficos)
            fig_top_pv.update_layout(
                title=dict(text=f"<b>{titulo_top5_pv}</b>"),
                xaxis=dict(title="<b>Qtd. Pedidos de Venda (PV)</b>"),
                yaxis=dict(title="<b>Cliente</b>"),
                margin=dict(l=180, r=40, t=50, b=40),
            )
            st.plotly_chart(fig_top_pv, use_container_width=True)
        else:
            st.info("Sem lançamentos de PVs para o filtro selecionado.")

    # --- RANKING TOP 10 FATURAMENTO MONETÁRIO ---
    st.divider()
    st.subheader(f"💎 Ranking Top 10 Clientes por Faturamento Monetário ({unidade_selecionada})")

    if df_fat_detalhado is not None:
        df_fd10 = df_fat_detalhado.copy()

        # Filtrar por Filial no detalhamento caso não seja "Todas as Unidades (Geral)"
        if unidade_selecionada != "Todas as Unidades (Geral)" and "Filial" in df_fd10.columns:
            codigo_filial = int(unidade_selecionada.split(" - ")[0])
            df_fd10 = df_fd10[df_fd10["Filial"] == codigo_filial]

        col_cli_10 = (
            "Cliente"
            if "Cliente" in df_fd10.columns
            else ("Nome Fantasia" if "Nome Fantasia" in df_fd10.columns else df_fd10.columns[2])
        )
        col_emissao_10 = (
            "Data"
            if "Data" in df_fd10.columns
            else ("Emissão" if "Emissão" in df_fd10.columns else df_fd10.columns[0])
        )
        col_valor_10 = (
            "R$ Fatur."
            if "R$ Fatur." in df_fd10.columns
            else ("Valor" if "Valor" in df_fd10.columns else ("Vlr Faturado" if "Vlr Faturado" in df_fd10.columns else df_fd10.columns[-1]))
        )

        df_fd10["DATA_STR"] = pd.to_datetime(df_fd10[col_emissao_10], errors="coerce").dt.strftime("%Y-%m-%d")
        datas_fat_disponiveis = sorted(df_fd10["DATA_STR"].dropna().unique())

        col_m, col_d = st.columns([2, 2])
        with col_m:
            modo_top10 = st.radio(
                "Modo de Exibição do Top 10 Faturamento:",
                ["Por Dia Selecionado", "Acumulado do Período Geral"],
                horizontal=True,
                key="modo_top10_fat",
            )

        if modo_top10 == "Por Dia Selecionado" and datas_fat_disponiveis:
            with col_d:
                data_fat_top10_sel = st.selectbox(
                    "Selecione a Data para Filtro de Faturamento:",
                    datas_fat_disponiveis,
                    index=len(datas_fat_disponiveis) - 1,
                    key="sel_fat_top10_date",
                )
            df_top10_filtrado = df_fd10[df_fd10["DATA_STR"] == data_fat_top10_sel]
            titulo_top10 = f"Top 10 Clientes no Dia: {data_fat_top10_sel}"
        else:
            df_top10_filtrado = df_fd10
            titulo_top10 = "Top 10 Clientes por Faturamento Acumulado"

        df_top10 = (
            df_top10_filtrado.groupby(col_cli_10)[col_valor_10]
            .sum()
            .reset_index(name="Total_Faturado")
            .sort_values("Total_Faturado", ascending=False)
            .head(10)
        )
        df_top10 = df_top10.sort_values("Total_Faturado", ascending=True)

        if not df_top10.empty:
            fig_top10 = go.Figure()
            fig_top10.add_trace(
                go.Bar(
                    y=df_top10[col_cli_10],
                    x=df_top10["Total_Faturado"],
                    orientation="h",
                    marker=dict(color="#118ab2", line=dict(color="#000000", width=1)),
                    text=[
                        f"<b>R$ {v:,.2f}</b>".replace(",", "X").replace(".", ",").replace("X", ".")
                        for v in df_top10["Total_Faturado"]
                    ],
                    textfont=dict(color="#ffffff", size=12),
                    textposition="auto",
                )
            )
            fig_top10.update_layout(**layout_graficos)
            fig_top10.update_layout(
                title=dict(text=f"<b>{titulo_top10}</b>"),
                xaxis=dict(title="<b>Valor Faturado (R$)</b>"),
                yaxis=dict(title="<b>Cliente</b>"),
                margin=dict(l=180, r=40, t=50, b=40),
            )
            st.plotly_chart(fig_top10, use_container_width=True)
        else:
            st.info("Sem dados de faturamento para o filtro selecionado.")

    # --- KPIS PREDITIVOS (ESTATÍSTICAS E ESTIMATIVAS) ---
    st.divider()
    st.subheader("🎯 KPIs Preditivos & Projeções de Desempenho")

    if not df_filtrado.empty:
        # Cálculo das médias e índices baseados nos últimos registros do período selecionado
        ultimos_dias = df_filtrado.tail(5) if len(df_filtrado) >= 5 else df_filtrado

        media_saudavel = df_filtrado["SAUDAVEL"].mean()
        media_backlog = df_filtrado["BACKLOG"].mean()
        media_skus = df_filtrado["Total_SKUs"].mean()
        media_fat_diaria = df_filtrado["Valor_Faturado"].mean()
        
        # Fator de conversão médio entre (Saudável + Backlog) e Expedição
        fator_conversao = (
            df_filtrado["Total_Expedidos"].sum() / (df_filtrado["SAUDAVEL"].sum() + df_filtrado["BACKLOG"].sum())
            if (df_filtrado["SAUDAVEL"].sum() + df_filtrado["BACKLOG"].sum()) > 0
            else 1.0
        )
        
        # Previsão da expedição do próximo ciclo
        prev_saudavel_tendencia = ultimos_dias["SAUDAVEL"].mean()
        prev_backlog_tendencia = ultimos_dias["BACKLOG"].mean()
        expedicao_preditiva_estimada = int((prev_saudavel_tendencia + prev_backlog_tendencia) * fator_conversao)

        p1, p2, p3, p4, p5 = st.columns(5)
        
        p1.metric(
            "📈 Média Saudável/Dia",
            f"{media_saudavel:.1f}",
            delta=f"{prev_saudavel_tendencia - media_saudavel:+.1f} (Recente)"
        )
        p2.metric(
            "⚠️ Média Backlog/Dia",
            f"{media_backlog:.1f}",
            delta=f"{prev_backlog_tendencia - media_backlog:+.1f} (Recente)",
            delta_color="inverse"
        )
        p3.metric(
            "📦 Média SKUs/Dia",
            f"{media_skus:.1f}"
        )
        p4.metric(
            "💵 Média Faturamento/Dia",
            f"R$ {media_fat_diaria:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )
        p5.metric(
            "🚚 Expedição Preditiva Estimada",
            f"{expedicao_preditiva_estimada} romaneios",
            help="Previsão baseada no índice de conversão da produção recente."
        )

    # --- TABELA CONSOLIDADA DETALHADA ---
    with st.expander("🔍 Visualizar Tabela Consolidada"):
        st.dataframe(
            df_filtrado[[
                "DATA",
                "Total_PVs",
                "SAUDAVEL",
                "BACKLOG",
                "Total_SKUs",
                "Valor_Faturado",
                "Total_Expedidos",
            ]],
            use_container_width=True,
        )


if __name__ == "__main__":
    main()