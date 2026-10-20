import io
import os
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from cryptography.fernet import Fernet
from sklearn.ensemble import RandomForestRegressor

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
  def load_encrypted_excel(
      encrypted_path: str, key: bytes, sheet_name=0
  ) -> pd.DataFrame:
    if not os.path.exists(encrypted_path):
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
  """Lê as novas planilhas diretamente do diretório back-end ./data/ ou raiz"""

  DATA_DIR = "./data/"

  def __init__(self, key: bytes = None):
    self.key = key

  def read_dataframe(self, filename: str, sheet_name=0) -> pd.DataFrame:
    path = os.path.join(self.DATA_DIR, filename)
    enc_path = path + ".enc"

    # 1. Tenta versão criptografada
    if self.key and os.path.exists(enc_path):
      try:
        return DataSecurityManager.load_encrypted_excel(
            enc_path, self.key, sheet_name
        )
      except Exception:
        pass

    # 2. Leitura direta do .xlsx na pasta ./data/
    if os.path.exists(path):
      try:
        return pd.read_excel(path, sheet_name=sheet_name)
      except Exception:
        try:
          return pd.read_excel(path, sheet_name=0)
        except Exception:
          return None

    # 3. Fallback para a raiz do projeto
    if os.path.exists(filename):
      try:
        return pd.read_excel(filename, sheet_name=sheet_name)
      except Exception:
        try:
          return pd.read_excel(filename, sheet_name=0)
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

    # Faturamento por cliente
    df_fat_detalhado = self.read_dataframe(
        "DadosFaturamento.xlsx", "Faturamento por cliente"
    )
    if df_fat_detalhado is None:
      df_fat_detalhado = self.read_dataframe("DadosFaturamento.xlsx", 0)

    return df_prod_bruto, df_prod_tratado, df_rom_tratado, df_fat_detalhado


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
        .logo-container {
            background-color: #ffffff; padding: 8px; border-radius: 10px;
            border: 1px solid #ced4da; text-align: center;
        }
        </style>
    """,
        unsafe_allow_html=True,
    )

  def render_header(self):
    col_logo1, col_titulo, col_logo2 = st.columns([1.2, 3.6, 1.2])
    with col_logo1:
      if os.path.exists("images.jpg"):
        st.markdown('<div class="logo-container">', unsafe_allow_html=True)
        st.image("images.jpg", width=100)
        st.markdown("</div>", unsafe_allow_html=True)
      else:
        st.write("Control Log")

    with col_titulo:
      st.title("Dashboard de Produção, Expedição & BI")
      st.markdown(
          "Monitoramento e consolidação de dados via **Back-End Seguro**."
      )

    with col_logo2:
      if os.path.exists("logo2.png"):
        st.markdown('<div class="logo-container">', unsafe_allow_html=True)
        st.image("logo2.png", width=120)
        st.markdown("</div>", unsafe_allow_html=True)
      else:
        st.write("Higimed")
    st.divider()


# ==========================================
# 4. EXECUÇÃO PRINCIPAL DO DASHBOARD
# ==========================================
def main():
  ui = DashboardUI()
  ui.render_header()

  os.makedirs("./data/", exist_ok=True)
  loader = DataLoader()
  df_prod_bruto, df_prod_tratado, df_rom_tratado, df_fat_detalhado = (
      loader.load_all_data()
  )

  if df_prod_tratado is None or df_rom_tratado is None:
    st.info(
        "📂 **Aguardando dados no Back-End:** Insira as planilhas"
        " (`DadosProducao.xlsx`, `DadosRomaneios.xlsx` e"
        " `DadosFaturamento.xlsx`) no diretório `./data/` para sincronização"
        " automática."
    )
    st.stop()

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

    df_prod_completo = pd.merge(
        df_sku_agg, df_status_agg, on="DATA", how="outer"
    ).fillna(0)
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

  # Merge exclusivo da série operacional
  df_diario = pd.merge(
      df_diario, df_r[["DATA", "Total_Expedidos"]], on="DATA", how="outer"
  ).fillna(0)

  # --- TRATAMENTO DE FATURAMENTO ---
  if df_fat_detalhado is not None:
    df_fd_calc = df_fat_detalhado.copy()

    col_f_emissao = (
        "Data"
        if "Data" in df_fd_calc.columns
        else (
            "Emissão"
            if "Emissão" in df_fd_calc.columns
            else df_fd_calc.columns[0]
        )
    )
    col_f_valor = (
        "R$ Fatur."
        if "R$ Fatur." in df_fd_calc.columns
        else (
            "Valor"
            if "Valor" in df_fd_calc.columns
            else (
                "Vlr Faturado"
                if "Vlr Faturado" in df_fd_calc.columns
                else df_fd_calc.columns[-1]
            )
        )
    )

    df_fd_calc["DATA"] = pd.to_datetime(
        df_fd_calc[col_f_emissao], errors="coerce"
    )
    df_fat_diario = (
        df_fd_calc.groupby("DATA")[col_f_valor]
        .sum()
        .reset_index(name="Valor_Faturado")
    )

    df_diario = pd.merge(df_diario, df_fat_diario, on="DATA", how="left").fillna(
        0
    )
  else:
    df_diario["Valor_Faturado"] = 0.0

  df_diario = df_diario.sort_values("DATA").reset_index(drop=True)

  # --- SELEÇÃO TEMPORAL (CALENDÁRIO / MÊS / SEMANA) ---
  st.subheader("📅 Filtro Temporal de Análise")
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
      dt_inicio = (
          df_diario[df_diario["Mes_Ano"] == mes_sel]["DATA"].min().date()
      )
      dt_fim = df_diario[df_diario["Mes_Ano"] == mes_sel]["DATA"].max().date()

    else:
      df_diario["Semana"] = (
          "Semana "
          + df_diario["DATA"].dt.isocalendar().week.astype(str)
          + " / "
          + df_diario["DATA"].dt.year.astype(str)
      )
      semanas = df_diario["Semana"].unique().tolist()
      semana_sel = st.selectbox(
          "Selecione a Semana:", semanas, index=len(semanas) - 1
      )
      dt_inicio = (
          df_diario[df_diario["Semana"] == semana_sel]["DATA"].min().date()
      )
      dt_fim = (
          df_diario[df_diario["Semana"] == semana_sel]["DATA"].max().date()
      )

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
      df_filtrado.to_excel(
          writer, sheet_name="Dados_Consolidados", index=False
      )

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

  if df_fat_detalhado is not None:
    df_fd_kpi = df_fat_detalhado.copy()
    col_f_emissao_k = (
        "Data"
        if "Data" in df_fd_kpi.columns
        else (
            "Emissão"
            if "Emissão" in df_fd_kpi.columns
            else df_fd_kpi.columns[0]
        )
    )
    col_f_valor_k = (
        "R$ Fatur."
        if "R$ Fatur." in df_fd_kpi.columns
        else (
            "Valor"
            if "Valor" in df_fd_kpi.columns
            else (
                "Vlr Faturado"
                if "Vlr Faturado" in df_fd_kpi.columns
                else df_fd_kpi.columns[-1]
            )
        )
    )
    df_fd_kpi["DT"] = pd.to_datetime(
        df_fd_kpi[col_f_emissao_k], errors="coerce"
    ).dt.date
    total_fat = df_fd_kpi[
        (df_fd_kpi["DT"] >= dt_inicio) & (df_fd_kpi["DT"] <= dt_fim)
    ][col_f_valor_k].sum()
  else:
    total_fat = 0.0

  k1.metric("📄 Total PVs", total_pvs)
  k2.metric("✅ Saudável", total_saudavel)
  k3.metric("⚠️ Backlog", total_backlog)
  k4.metric("📦 Total SKUs", total_skus)
  k5.metric(
      "💰 Faturamento Total",
      f"R$ {total_fat:,.2f}".replace(",", "X")
      .replace(".", ",")
      .replace("X", "."),
  )

  layout_graficos = dict(
      template="plotly_white",
      plot_bgcolor="rgba(0,0,0,0)",
      paper_bgcolor="rgba(0,0,0,0)",
      font=dict(color="#000000", size=13, family="Arial"),
      margin=dict(l=40, r=40, t=50, b=40),
  )

  # --- GRÁFICO 1: PRODUÇÃO VS FATURAMENTO ---
  st.subheader("💵 Produção Diária: Pedidos de Venda (PV) vs. Valor Faturado (R$)")
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
          name="Faturamento (R$)",
          mode="lines+markers+text",
          text=[
              f"<b>R$ {v:,.0f}</b>".replace(",", ".")
              for v in df_filtrado["Valor_Faturado"]
          ],
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
          text=[
              f"<b>{int(v)}</b>" if v > 0 else ""
              for v in df_filtrado["SAUDAVEL"]
          ],
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
          text=[
              f"<b>{int(v)}</b>" if v > 0 else ""
              for v in df_filtrado["BACKLOG"]
          ],
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
  fig_comp.update_layout(
      barmode="group", yaxis=dict(title="<b>Quantidade</b>")
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
    col_pb_dt = (
        "DATA" if "DATA" in df_pb_cliente.columns else df_pb_cliente.columns[2]
    )
    df_pb_cliente["DATA_STR"] = pd.to_datetime(
        df_pb_cliente[col_pb_dt], errors="coerce"
    ).dt.strftime("%Y-%m-%d")

    datas_p_disp = sorted(df_pb_cliente["DATA_STR"].dropna().unique())
    if datas_p_disp:
      data_p_sel = st.selectbox(
          "Selecione a Data para visualizar o Top 5 PVs:",
          datas_p_disp,
          index=len(datas_p_disp) - 1,
          key="sel_top5_pv",
      )

      df_top_dia = df_pb_cliente[df_pb_cliente["DATA_STR"] == data_p_sel]
      df_ranking_pv = (
          df_top_dia.groupby("CLIENTE")["PV"]
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
                marker=dict(
                    color="#3a86ff", line=dict(color="#000000", width=1)
                ),
                text=[f"<b>{int(v)} PVs</b>" for v in df_ranking_pv["Qtd_PVs"]],
                textfont=dict(color="#ffffff", size=12),
                textposition="auto",
            )
        )
        fig_top_pv.update_layout(**layout_graficos)
        fig_top_pv.update_layout(
            xaxis=dict(title="<b>Qtd. Pedidos de Venda (PV)</b>"),
            yaxis=dict(title="<b>Cliente</b>"),
            margin=dict(l=180, r=40, t=30, b=40),
        )
        st.plotly_chart(fig_top_pv, use_container_width=True)

  # --- RANKING TOP 10 FATURAMENTO MONETÁRIO ---
  st.divider()
  st.subheader("💎 Ranking Top 10 Clientes por Faturamento Monetário (R$)")

  if df_fat_detalhado is not None:
    df_fd10 = df_fat_detalhado.copy()

    col_cli_10 = (
        "Cliente"
        if "Cliente" in df_fd10.columns
        else (
            "Nome Fantasia"
            if "Nome Fantasia" in df_fd10.columns
            else df_fd10.columns[2]
        )
    )
    col_emissao_10 = (
        "Data"
        if "Data" in df_fd10.columns
        else (
            "Emissão" if "Emissão" in df_fd10.columns else df_fd10.columns[0]
        )
    )
    col_valor_10 = (
        "R$ Fatur."
        if "R$ Fatur." in df_fd10.columns
        else (
            "Valor"
            if "Valor" in df_fd10.columns
            else (
                "Vlr Faturado"
                if "Vlr Faturado" in df_fd10.columns
                else df_fd10.columns[-1]
            )
        )
    )

    df_fd10["DATA_DT"] = pd.to_datetime(
        df_fd10[col_emissao_10], errors="coerce"
    ).dt.date
    df_fd10_filtrado = df_fd10[
        (df_fd10["DATA_DT"] >= dt_inicio) & (df_fd10["DATA_DT"] <= dt_fim)
    ]

    df_top10 = (
        df_fd10_filtrado.groupby(col_cli_10)[col_valor_10]
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
                  f"<b>R$ {v:,.2f}</b>".replace(",", "X")
                  .replace(".", ",")
                  .replace("X", ".")
                  for v in df_top10["Total_Faturado"]
              ],
              textfont=dict(color="#ffffff", size=12),
              textposition="auto",
          )
      )
      fig_top10.update_layout(**layout_graficos)
      fig_top10.update_layout(
          xaxis=dict(title="<b>Valor Faturado (R$)</b>"),
          yaxis=dict(title="<b>Cliente</b>"),
          margin=dict(l=180, r=40, t=30, b=40),
      )
      st.plotly_chart(fig_top10, use_container_width=True)
    else:
      st.info("Sem dados de faturamento para o período filtrado.")

  # --- MACHINE LEARNING ---
  st.divider()
  st.subheader("🤖 Modelo Preditivo de Machine Learning")

  col_ml1, col_ml2 = st.columns(2)

  with col_ml1:
    st.markdown("### 📈 Simulação de Capacidade de Expedição")
    input_saudavel = st.slider(
        "Meta de Notas Saudáveis:",
        0,
        150,
        int(df_filtrado["SAUDAVEL"].mean())
        if not df_filtrado.empty
        else 10,
    )
    input_backlog = st.slider(
        "Meta de Backlog:",
        0,
        150,
        int(df_filtrado["BACKLOG"].mean())
        if not df_filtrado.empty
        else 10,
    )
    input_skus = st.slider(
        "Estimativa de SKUs:",
        50,
        500,
        int(df_filtrado["Total_SKUs"].mean())
        if not df_filtrado.empty
        else 100,
    )

    X = df_filtrado[["SAUDAVEL", "BACKLOG", "Total_SKUs"]]
    y = df_filtrado["Total_Expedidos"]

    if len(df_filtrado) >= 3:
      rf_model = RandomForestRegressor(n_estimators=100, random_state=42)
      rf_model.fit(X, y)

      pred_expedicao = rf_model.predict(
          [[input_saudavel, input_backlog, input_skus]]
      )[0]

      st.success(
          f"**Expedição Preditiva Estimada:** `{int(pred_expedicao)}` volumes"
          " / romaneios."
      )
    else:
      st.info("Selecione um período maior para treinar o modelo preditivo.")

  with col_ml2:
    st.markdown("### 📊 Estatísticas Diárias do Período")
    st.write(
        "- **Média de Notas Saudáveis/dia:**"
        f" `{df_filtrado['SAUDAVEL'].mean():.2f}`"
    )
    st.write(
        f"- **Média de Backlog/dia:** `{df_filtrado['BACKLOG'].mean():.2f}`"
    )
    st.write(
        "- **Média Diária de SKUs:**"
        f" `{df_filtrado['Total_SKUs'].mean():.2f}`"
    )
    st.write(
        "- **Média de Faturamento/dia:**"
        f" `R$ {df_filtrado['Valor_Faturado'].mean():,.2f}`"
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