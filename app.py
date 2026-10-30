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

        if self.key and os.path.exists(enc_path):
            try:
                return DataSecurityManager.load_encrypted_excel(enc_path, self.key, sheet_name)
            except Exception:
                pass

        if os.path.exists(path):
            try:
                return pd.read_excel(path, sheet_name=sheet_name, header=header)
            except Exception:
                try:
                    return pd.read_excel(path, sheet_name=0, header=header)
                except Exception:
                    return None

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
        df_prod_bruto = self.read_dataframe("DadosProducao.xlsx", "DadosBrutos")
        df_prod_tratado = self.read_dataframe("DadosProducao.xlsx", "LimpezaDados")

        df_rom_tratado = self.read_dataframe("DadosRomaneios.xlsx", "DadosRomaneios")
        if df_rom_tratado is None:
            df_rom_tratado = self.read_dataframe("DadosRomaneios.xlsx", "Planilha1")

        df_fat_detalhado = self.read_dataframe("DadosFaturamento.xlsx", "Faturamento por cliente")
        if df_fat_detalhado is None:
            df_fat_detalhado = self.read_dataframe("DadosFaturamento.xlsx", 0)

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
            h1, h2, h3, h4, h5, h6 { color: #000000 !important; font-weight: 900 !important; }
            p, span, label, div, .stMarkdown { color: #000000 !important; font-weight: 700; font-size: 16px !important; }
            [data-testid="stMetric"] {
                background-color: #ffffff; padding: 20px; border-radius: 12px;
                border: 2px solid #adb5bd; box-shadow: 0 4px 10px rgba(0,0,0,0.1);
            }
            [data-testid="stMetricLabel"] { color: #000000 !important; font-weight: 900 !important; font-size: 17px !important; }
            [data-testid="stMetricValue"] { color: #000000 !important; font-weight: 900 !important; font-size: 30px !important; }
            .brand-logo-text { font-size: 22px; font-weight: 900; color: #0077b6; text-align: center; }
            </style>
        """,
            unsafe_allow_html=True,
        )

    def render_header(self):
        col_logo1, col_titulo, col_logo2 = st.columns([1.2, 3.6, 1.2])
        
        with col_logo1:
            if os.path.exists("logo_control.png"):
                st.image("logo_control.png", width=130)
            elif os.path.exists("logo.png"):
                st.image("logo.png", width=130)
            elif os.path.exists("images.jpg"):
                st.image("images.jpg", width=130)
            else:
                st.markdown('<div class="brand-logo-text">CONTROL LOG</div>', unsafe_allow_html=True)

        with col_titulo:
            st.title("Dashboard de Produção, Expedição & BI")
            st.markdown("Monitoramento e consolidação de dados via **Back-End Seguro**.")

        with col_logo2:
            if os.path.exists("logo_master.png"):
                st.image("logo_master.png", width=150)
            elif os.path.exists("master.png"):
                st.image("master.png", width=150)
            elif os.path.exists("logo2.png"):
                st.image("logo2.png", width=150)
            elif os.path.exists("higimed.png"):
                st.image("higimed.png", width=150)
            else:
                st.markdown('<div class="brand-logo-text">MASTER HIGIMED</div>', unsafe_allow_html=True)
                
        st.divider()


# ==========================================
# 4. TRATAMENTO DE FATURAMENTO POR FILIAL
# ==========================================
def parse_faturamento_filiais(df_raw):
    if df_raw is None or df_raw.empty:
        return pd.DataFrame()

    df_data = df_raw.iloc[2:].copy()
    col_data = pd.to_datetime(df_data.iloc[:, 0], errors="coerce")
    
    # 0101 - Matriz
    matriz_fat = pd.to_numeric(df_data.iloc[:, 1], errors="coerce").fillna(0)
    matriz_dev = abs(pd.to_numeric(df_data.iloc[:, 2], errors="coerce").fillna(0))
    
    # 0102 - Filial RJ
    rj_fat = pd.to_numeric(df_data.iloc[:, 3], errors="coerce").fillna(0)
    rj_dev = abs(pd.to_numeric(df_data.iloc[:, 4], errors="coerce").fillna(0))
    
    # 0103 - Filial CP
    cp_fat = pd.to_numeric(df_data.iloc[:, 5], errors="coerce").fillna(0)
    cp_dev = abs(pd.to_numeric(df_data.iloc[:, 6], errors="coerce").fillna(0))
    
    # 0104 - Filial SBC
    sbc_fat = pd.to_numeric(df_data.iloc[:, 7], errors="coerce").fillna(0)
    sbc_dev = abs(pd.to_numeric(df_data.iloc[:, 8], errors="coerce").fillna(0))
    
    # GERAL (Coluna J e K)
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

    df_fat_unidades = parse_faturamento_filiais(df_fat_bruto_raw)

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

    # Merge do Faturamento sem perdas de datas (Outer Join)
    if not df_fat_unidades.empty:
        df_diario = pd.merge(df_diario, df_fat_unidades, on="DATA", how="outer").fillna(0)

    df_diario = df_diario.sort_values("DATA").reset_index(drop=True)

    # ==========================================
    # 1. SELEÇÃO TEMPORAL GERAL DA OPERAÇÃO
    # ==========================================
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
    df_filtrado["Data_Str"] = df_filtrado["DATA"].dt.strftime("%d/%m")

    # Identificar a menor data real de Produção para os gráficos específicos de fábrica
    if "df_p" in locals() and df_p is not None and "DATA" in df_p.columns and not df_p["DATA"].dropna().empty:
        data_min_prod = df_p["DATA"].dropna().min()
        df_filtrado_prod = df_filtrado[df_filtrado["DATA"] >= data_min_prod].copy()
    else:
        df_filtrado_prod = df_filtrado.copy()

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

    # --- INDICADORES GERAIS DE PRODUÇÃO ---
    st.markdown("### 📊 Indicadores Gerais de Produção")
    k1, k2, k3, k4 = st.columns(4)
    total_pvs = int(df_filtrado["Total_PVs"].sum())
    total_saudavel = int(df_filtrado["SAUDAVEL"].sum())
    total_backlog = int(df_filtrado["BACKLOG"].sum())
    total_skus = int(df_filtrado["Total_SKUs"].sum())

    k1.metric("📄 Total PVs", total_pvs)
    k2.metric("✅ Saudável", total_saudavel)
    k3.metric("⚠️ Backlog", total_backlog)
    k4.metric("📦 Total SKUs", total_skus)

    st.divider()

    # ==========================================
    # 2. SEÇÃO DE FATURAMENTO E DEVOLUÇÕES
    # ==========================================
    col_filial_sel, col_space_f = st.columns([2, 2])
    with col_filial_sel:
        opcoes_filiais = [
            "Todas as Unidades (Geral)",
            "0101 - Matriz",
            "0102 - Filial RJ",
            "0103 - Filial CP",
            "0104 - Filial SBC"
        ]
        unidade_selecionada = st.selectbox(
            "🏢 Selecione a Unidade / Filial (Filtro Exclusivo de Faturamento):",
            opcoes_filiais,
            index=0,
            key="seletor_unidade_filial_fatur"
        )

    col_fat_ativa = f"{unidade_selecionada}_Fat"
    col_dev_ativa = f"{unidade_selecionada}_Dev"

    fat_total_exclusivo = df_filtrado[col_fat_ativa].sum() if col_fat_ativa in df_filtrado.columns else 0.0
    dev_total_exclusivo = df_filtrado[col_dev_ativa].sum() if col_dev_ativa in df_filtrado.columns else 0.0

    dias_com_fat = len(df_filtrado[df_filtrado[col_fat_ativa] > 0])
    divisor_dias = dias_com_fat if dias_com_fat > 0 else 1
    media_fat_diaria = fat_total_exclusivo / divisor_dias
    media_dev_diaria = dev_total_exclusivo / divisor_dias

    st.markdown(f"### 💰 Faturamento & Devoluções ({unidade_selecionada})")
    kf1, kf2, kf3, kf4 = st.columns(4)
    
    label_fat = f"Faturamento Total ({unidade_selecionada})"
    
    kf1.metric(
        f"💵 {label_fat}",
        f"R$ {fat_total_exclusivo:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
    )
    kf2.metric(
        f"🔴 Total Devoluções ({unidade_selecionada})",
        f"R$ {dev_total_exclusivo:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
    )
    kf3.metric(
        "📊 Média Faturada/Dia",
        f"R$ {media_fat_diaria:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
    )
    kf4.metric(
        "📉 Média Devolução/Dia",
        f"R$ {media_dev_diaria:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
    )

    # --- GRÁFICO 1: FATURAMENTO BRUTO VS DEVOLUÇÕES (EXIBE A PARTIR DO DIA 01 E SEM SOBREPOSIÇÃO) ---
    if not df_filtrado.empty:
        fig_fat_solo = go.Figure()

        def fmt_brl(val):
            if val >= 1_000_000:
                return f"<b>R$ {val/1_000_000:.2f}M</b>".replace(".", ",")
            elif val >= 1_000:
                return f"<b>R$ {val/1_000:.0f}k</b>"
            elif val > 0:
                return f"<b>R$ {val:.0f}</b>"
            return ""

        labels_fat = [fmt_brl(v) for v in df_filtrado[col_fat_ativa]]
        labels_dev = [fmt_brl(v) if v > 0 else "" for v in df_filtrado[col_dev_ativa]]

        max_fat = df_filtrado[col_fat_ativa].max() if not df_filtrado[col_fat_ativa].empty else 1000
        max_dev = df_filtrado[col_dev_ativa].max() if not df_filtrado[col_dev_ativa].empty else 1000

        # Barras de Faturamento com colunas mais largas (bargap=0.10) e texto no topo outside
        fig_fat_solo.add_trace(
            go.Bar(
                x=df_filtrado["Data_Str"],
                y=df_filtrado[col_fat_ativa],
                name="Faturamento (R$)",
                marker=dict(color="#0077b6", line=dict(color="#000000", width=1.0)),
                text=labels_fat,
                textfont=dict(color="#000000", size=12),
                textposition="outside",
                cliponaxis=False,
            )
        )

        # Posicionamento inteligente para o texto de devoluções (bottom center abaixo do ponto para afastar da barra de faturamento)
        fig_fat_solo.add_trace(
            go.Scatter(
                x=df_filtrado["Data_Str"],
                y=df_filtrado[col_dev_ativa],
                name="Devoluções (R$)",
                mode="lines+markers+text",
                marker=dict(color="#d90429", size=6, symbol="circle"),
                line=dict(color="#d90429", width=1.8),
                text=labels_dev,
                textfont=dict(color="#a10011", size=11),
                textposition="bottom center",
                yaxis="y2",
                cliponaxis=False,
            )
        )

        fig_fat_solo.update_layout(
            template="plotly_white",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#000000", size=14, family="Arial"),
            margin=dict(l=65, r=65, t=85, b=85),
            height=640,
            bargap=0.10,
            yaxis=dict(
                title=dict(text="<b>Faturamento Monetário (R$)</b>", font=dict(size=15)),
                tickprefix="R$ ",
                showgrid=True,
                gridcolor="#e9ecef",
                tickfont=dict(size=13),
                range=[0, max_fat * 1.25] if max_fat > 0 else None,
            ),
            yaxis2=dict(
                title=dict(text="<b>Devoluções (R$)</b>", font=dict(size=15)),
                overlaying="y",
                side="right",
                showgrid=False,
                tickfont=dict(size=13),
                range=[0, max_dev * 1.40] if max_dev > 0 else None,
            ),
            xaxis=dict(
                title=dict(text="<b>Data (Dia/Mês)</b>", font=dict(size=15)),
                type="category",
                tickfont=dict(size=13),
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.03,
                xanchor="right",
                x=1,
                font=dict(size=13),
            ),
        )
        st.plotly_chart(fig_fat_solo, use_container_width=True)

    st.divider()

    # ==========================================
    # 3. MÉDIAS DIÁRIAS DO PERÍODO & MODELOS PREDITIVOS
    # ==========================================
    st.markdown("### 🎯 Médias Diárias do Período & Modelos Preditivos")
    
    if not df_filtrado.empty:
        media_saudavel = df_filtrado["SAUDAVEL"].mean()
        media_backlog = df_filtrado["BACKLOG"].mean()
        media_skus = df_filtrado["Total_SKUs"].mean()

        # Filtrar dias com atividade real de expedição
        df_exp = df_filtrado[df_filtrado["Total_Expedidos"] > 0]
        if df_exp.empty:
            df_exp = df_filtrado

        media_expedidos = df_exp["Total_Expedidos"].mean()

        df_recentes = df_filtrado.tail(5)
        weights = np.linspace(1, 2, len(df_recentes)) if len(df_recentes) > 0 else [1]
        weights /= weights.sum()

        pred_saudavel = np.dot(df_recentes["SAUDAVEL"], weights) if len(df_recentes) > 0 else media_saudavel
        pred_backlog = np.dot(df_recentes["BACKLOG"], weights) if len(df_recentes) > 0 else media_backlog
        pred_skus = np.dot(df_recentes["Total_SKUs"], weights) if len(df_recentes) > 0 else media_skus

        df_exp_recentes = df_exp.tail(5)
        weights_exp = np.linspace(1, 2, len(df_exp_recentes)) if len(df_exp_recentes) > 0 else [1]
        weights_exp /= weights_exp.sum()
        pred_expedidos = np.dot(df_exp_recentes["Total_Expedidos"], weights_exp) if len(df_exp_recentes) > 0 else media_expedidos

        pm1, pm2, pm3, pm4, pm5 = st.columns(5)
        pm1.metric(
            "📈 Média Saudável/Dia",
            f"{media_saudavel:.1f}",
            delta=f"{pred_saudavel - media_saudavel:+.1f} Projeção"
        )
        pm2.metric(
            "⚠️ Média Backlog/Dia",
            f"{media_backlog:.1f}",
            delta=f"{pred_backlog - media_backlog:+.1f} Projeção",
            delta_color="inverse"
        )
        pm3.metric(
            "📦 Média SKUs/Dia",
            f"{media_skus:.1f}",
            delta=f"{pred_skus - media_skus:+.1f} Projeção"
        )
        pm4.metric(
            "💵 Média Faturada/Dia",
            f"R$ {media_fat_diaria:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            help=f"Média calculada para a unidade selecionada ({unidade_selecionada})."
        )
        pm5.metric(
            "🚚 Média Preditiva de Expedição",
            f"{pred_expedidos:.1f} vol.",
            delta=f"{pred_expedidos - media_expedidos:+.1f} Projeção",
            help="Média Preditiva baseada no histórico de notas com romaneio e expedição realizada."
        )

    # ==========================================
    # GRÁFICO 3: PRODUÇÃO DIÁRIA (PV) VS FATURAMENTO
    # ==========================================
    st.subheader(f"💵 Produção Diária: Pedidos de Venda (PV) vs. Faturamento ({unidade_selecionada})")
    fig_fat = go.Figure()
    fig_fat.add_trace(
        go.Bar(
            x=df_filtrado_prod["Data_Str"],
            y=df_filtrado_prod["Total_PVs"],
            name="PVs",
            marker=dict(color="#0077b6", line=dict(color="#000000", width=1)),
            text=[f"<b>{int(v)}</b>" for v in df_filtrado_prod["Total_PVs"]],
            textfont=dict(color="#ffffff", size=14),
            textposition="auto",
        )
    )
    fig_fat.add_trace(
        go.Scatter(
            x=df_filtrado_prod["Data_Str"],
            y=df_filtrado_prod[col_fat_ativa],
            name="Faturamento",
            mode="lines+markers+text",
            text=[fmt_brl(v) for v in df_filtrado_prod[col_fat_ativa]],
            textfont=dict(color="#000000", size=13),
            textposition="top center",
            marker=dict(color="#2ec4b6", size=9),
            line=dict(color="#2ec4b6", width=3.5),
            yaxis="y2",
        )
    )
    fig_fat.update_layout(
        template="plotly_white",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#000000", size=15, family="Arial"),
        margin=dict(l=65, r=65, t=75, b=85),
        height=620,
        yaxis=dict(
            title=dict(text="<b>Qtd. Pedidos (PV)</b>", font=dict(size=16)),
            tickfont=dict(size=14),
        ),
        yaxis2=dict(
            title=dict(text="<b>Valor Faturado (R$)</b>", font=dict(size=16)),
            overlaying="y",
            side="right",
            showgrid=False,
            tickfont=dict(size=14),
        ),
        xaxis=dict(
            type="category",
            tickfont=dict(size=14),
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=14),
        ),
    )
    st.plotly_chart(fig_fat, use_container_width=True)

    # ==========================================
    # GRÁFICO 4: PRODUÇÃO DIÁRIA (PV) VS SKUs
    # ==========================================
    st.subheader("📊 Produção Diária: Pedidos de Venda (PV) vs. SKUs")
    fig_sku = go.Figure()
    fig_sku.add_trace(
        go.Bar(
            x=df_filtrado_prod["Data_Str"],
            y=df_filtrado_prod["Total_PVs"],
            name="PVs",
            marker=dict(color="#0077b6", line=dict(color="#000000", width=1)),
            text=[f"<b>{int(v)}</b>" for v in df_filtrado_prod["Total_PVs"]],
            textfont=dict(color="#ffffff", size=14),
            textposition="auto",
        )
    )
    fig_sku.add_trace(
        go.Scatter(
            x=df_filtrado_prod["Data_Str"],
            y=df_filtrado_prod["Total_SKUs"],
            name="SKUs",
            mode="lines+markers+text",
            text=[f"<b>{int(v)}</b>" for v in df_filtrado_prod["Total_SKUs"]],
            textfont=dict(color="#000000", size=13),
            textposition="top center",
            marker=dict(color="#d97706", size=9),
            line=dict(color="#d97706", width=3.5),
            yaxis="y2",
        )
    )
    fig_sku.update_layout(
        template="plotly_white",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#000000", size=15, family="Arial"),
        margin=dict(l=65, r=65, t=75, b=85),
        height=620,
        yaxis=dict(
            title=dict(text="<b>Qtd. Pedidos (PV)</b>", font=dict(size=16)),
            tickfont=dict(size=14),
        ),
        yaxis2=dict(
            title=dict(text="<b>Total SKUs</b>", font=dict(size=16)),
            overlaying="y",
            side="right",
            showgrid=False,
            tickfont=dict(size=14),
        ),
        xaxis=dict(
            type="category",
            tickfont=dict(size=14),
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=14),
        ),
    )
    st.plotly_chart(fig_sku, use_container_width=True)

    # ==========================================
    # GRÁFICO 5: SAUDÁVEL VS BACKLOG
    # ==========================================
    st.subheader("📋 Produção Diária Isolada: Notas Saudáveis vs. Backlog")
    fig_status = go.Figure()
    fig_status.add_trace(
        go.Bar(
            x=df_filtrado_prod["Data_Str"],
            y=df_filtrado_prod["SAUDAVEL"],
            name="Notas Saudáveis",
            marker=dict(color="#0f9f90", line=dict(color="#000000", width=1)),
            text=[f"<b>{int(v)}</b>" if v > 0 else "" for v in df_filtrado_prod["SAUDAVEL"]],
            textfont=dict(color="#ffffff", size=13),
            textposition="auto",
        )
    )
    fig_status.add_trace(
        go.Bar(
            x=df_filtrado_prod["Data_Str"],
            y=df_filtrado_prod["BACKLOG"],
            name="Backlog",
            marker=dict(color="#d9381e", line=dict(color="#000000", width=1)),
            text=[f"<b>{int(v)}</b>" if v > 0 else "" for v in df_filtrado_prod["BACKLOG"]],
            textfont=dict(color="#ffffff", size=13),
            textposition="auto",
        )
    )
    fig_status.update_layout(
        template="plotly_white",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#000000", size=15, family="Arial"),
        margin=dict(l=65, r=65, t=75, b=85),
        height=620,
        barmode="stack",
        yaxis=dict(
            title=dict(text="<b>Quantidade de Pedidos (PV)</b>", font=dict(size=16)),
            tickfont=dict(size=14),
        ),
        xaxis=dict(
            type="category",
            tickfont=dict(size=14),
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=14),
        ),
    )
    st.plotly_chart(fig_status, use_container_width=True)

    # ==========================================
    # GRÁFICO 6: PRODUÇÃO VS EXPEDIÇÃO / ROMANEIOS
    # ==========================================
    st.subheader("🚚 Comparativo: Pedidos Produzidos (PV) vs. Expedições")
    fig_comp = go.Figure()
    fig_comp.add_trace(
        go.Bar(
            x=df_filtrado_prod["Data_Str"],
            y=df_filtrado_prod["Total_PVs"],
            name="Produzidos no Dia",
            marker=dict(color="#0f9f90", line=dict(color="#000000", width=1)),
            text=[f"<b>{int(v)}</b>" for v in df_filtrado_prod["Total_PVs"]],
            textfont=dict(color="#ffffff", size=13),
            textposition="auto",
        )
    )
    fig_comp.add_trace(
        go.Bar(
            x=df_filtrado_prod["Data_Str"],
            y=df_filtrado_prod["Total_Expedidos"],
            name="Expedidos no Dia (Romaneio)",
            marker=dict(color="#d9381e", line=dict(color="#000000", width=1)),
            text=[f"<b>{int(v)}</b>" for v in df_filtrado_prod["Total_Expedidos"]],
            textfont=dict(color="#ffffff", size=13),
            textposition="auto",
        )
    )
    fig_comp.update_layout(
        template="plotly_white",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#000000", size=15, family="Arial"),
        margin=dict(l=65, r=65, t=75, b=85),
        height=620,
        barmode="group",
        yaxis=dict(
            title=dict(text="<b>Quantidade</b>", font=dict(size=16)),
            tickfont=dict(size=14),
        ),
        xaxis=dict(
            type="category",
            tickfont=dict(size=14),
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=14),
        ),
    )
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
                    textfont=dict(color="#ffffff", size=13),
                    textposition="auto",
                )
            )
            fig_top_pv.update_layout(
                template="plotly_white",
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#000000", size=15, family="Arial"),
                height=620,
                title=dict(text=f"<b>{titulo_top5_pv}</b>"),
                xaxis=dict(title=dict(text="<b>Qtd. Pedidos de Venda (PV)</b>", font=dict(size=15))),
                yaxis=dict(title=dict(text="<b>Cliente</b>", font=dict(size=15))),
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
                    textfont=dict(color="#ffffff", size=13),
                    textposition="auto",
                )
            )
            fig_top10.update_layout(
                template="plotly_white",
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#000000", size=15, family="Arial"),
                height=620,
                title=dict(text=f"<b>{titulo_top10}</b>"),
                xaxis=dict(title=dict(text="<b>Valor Faturado (R$)</b>", font=dict(size=15))),
                yaxis=dict(title=dict(text="<b>Cliente</b>", font=dict(size=15))),
                margin=dict(l=180, r=40, t=50, b=40),
            )
            st.plotly_chart(fig_top10, use_container_width=True)
        else:
            st.info("Sem dados de faturamento para o filtro selecionado.")

    # --- TABELA CONSOLIDADA DETALHADA ---
    with st.expander("🔍 Visualizar Tabela Consolidada"):
        st.dataframe(
            df_filtrado[[
                "DATA",
                "Total_PVs",
                "SAUDAVEL",
                "BACKLOG",
                "Total_SKUs",
                col_fat_ativa,
                col_dev_ativa,
                "Total_Expedidos",
            ]],
            use_container_width=True,
        )


if __name__ == "__main__":
    main()