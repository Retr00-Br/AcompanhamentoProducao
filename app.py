import os
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from sklearn.ensemble import RandomForestRegressor

# Configuração da página
st.set_page_config(
    page_title="Dashboard - Logística & Operação", page_icon="📦", layout="wide"
)

# --- ESTILIZAÇÃO CSS CUSTOMIZADA ---
st.markdown(
    """
    <style>
    .main {
        background-color: #0b132b;
        color: #ffffff;
    }
    [data-testid="stSidebar"] {
        background-color: #1c2541;
        color: #ffffff;
    }
    [data-testid="stMetric"] {
        background-color: #1c2541;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #3a506b;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    [data-testid="stMetricLabel"] {
        color: #a5c4d4 !important;
        font-weight: 600;
    }
    [data-testid="stMetricValue"] {
        color: #ffffff !important;
        font-weight: 700;
    }
    h1, h2, h3 {
        color: #ffffff !important;
        font-weight: 800;
    }
    p, span, label {
        color: #d8e2dc !important;
    }
    .logo-container {
        background-color: #ffffff;
        padding: 8px;
        border-radius: 10px;
        text-align: center;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# --- CABEÇALHO E LOGOS ---
col_logo1, col_titulo, col_logo2 = st.columns([1.2, 3.6, 1.2])

with col_logo1:
  if os.path.exists("images.jpg"):
    st.markdown('<div class="logo-container">', unsafe_allow_html=True)
    st.image("images.jpg", width=100)
    st.markdown("</div>", unsafe_allow_html=True)
  else:
    st.write("Control Log")

with col_titulo:
  st.title("Dashboard de Produção e Expedição")
  st.markdown(
      "Controle diário de **PVs**, **SKUs**, **Faturamento**, **Status"
      " (Saudável / Backlog)** e **Romaneios**."
  )

with col_logo2:
  if os.path.exists("logo2.png"):
    st.markdown(
        '<div class="logo-container" style="background-color: #1c2541;">',
        unsafe_allow_html=True,
    )
    st.image("logo2.png", width=120)
    st.markdown("</div>", unsafe_allow_html=True)
  else:
    st.write("Higimed")

st.divider()

# --- UPLOAD DE ARQUIVOS (INTERFACE CLEAN) ---
st.sidebar.header("📁 Upload de Arquivos")
uploaded_prod = st.sidebar.file_uploader(
    "Planilha de Produção (.xlsx)", type=["xlsx"]
)
uploaded_rom = st.sidebar.file_uploader(
    "Planilha de Romaneios (.xlsx)", type=["xlsx"]
)


@st.cache_data
def load_data(file_p, file_r):
  df_prod_bruto, df_prod_tratado = None, None
  df_rom_bruto, df_rom_tratado = None, None
  df_fat = None

  file_p_path = file_p if file_p is not None else "DadosProducao.xlsx"
  if os.path.exists(file_p_path) or file_p is not None:
    try:
      df_prod_bruto = pd.read_excel(file_p_path, sheet_name="DadosBrutos")
      df_prod_tratado = pd.read_excel(file_p_path, sheet_name="LimpezaDados")

      # Leitura da aba de Faturamento (DadosFaturamento)
      excel_p = pd.ExcelFile(file_p_path)
      if "DadosFaturamento" in excel_p.sheet_names:
        df_fat = pd.read_excel(file_p_path, sheet_name="DadosFaturamento")
    except Exception as e:
      st.error(f"Erro ao carregar Produção/Faturamento: {e}")

  file_r_path = file_r if file_r is not None else "DadosRomaneios.xlsx"
  if os.path.exists(file_r_path) or file_r is not None:
    try:
      df_rom_bruto = pd.read_excel(file_r_path, sheet_name="Romaneios")
      df_rom_tratado = pd.read_excel(file_r_path, sheet_name="Planilha1")
    except Exception as e:
      st.error(f"Erro ao carregar Romaneios: {e}")

  return df_prod_bruto, df_prod_tratado, df_rom_bruto, df_rom_tratado, df_fat


(
    df_prod_bruto,
    df_prod_tratado,
    df_rom_bruto,
    df_rom_tratado,
    df_fat,
) = load_data(uploaded_prod, uploaded_rom)

if df_prod_tratado is None or df_rom_tratado is None:
  st.warning("Por favor, faça o upload das planilhas na barra lateral para iniciar.")
  st.stop()

# --- CONSOLIDAÇÃO DOS DADOS DIÁRIOS ---
# 1. Produção (Quantidade de PVs)
df_p = df_prod_tratado.copy()
df_p["DATA"] = pd.to_datetime(df_p["DATA"], errors="coerce")
df_p.rename(columns={"Quantidade": "Total_PVs"}, inplace=True)

# 2. SKUs e Status (Dados Brutos)
if df_prod_bruto is not None:
  df_pb = df_prod_bruto.copy()
  df_pb["DATA"] = pd.to_datetime(df_pb["DATA"], errors="coerce")

  df_status_agg = (
      df_pb.groupby(["DATA", "STATUS"])
      .size()
      .unstack(fill_value=0)
      .reset_index()
  )

  if "SAUDAVEL" not in df_status_agg.columns:
    df_status_agg["SAUDAVEL"] = 0
  if "BACKLOG" not in df_status_agg.columns:
    df_status_agg["BACKLOG"] = 0

  df_sku_agg = (
      df_pb.groupby("DATA")["SKU'S"].sum().reset_index(name="Total_SKUs")
  )

  df_prod_completo = pd.merge(
      df_sku_agg, df_status_agg, on="DATA", how="outer"
  ).fillna(0)
  df_diario = pd.merge(df_p, df_prod_completo, on="DATA", how="left").fillna(0)
else:
  df_diario = df_p
  df_diario["Total_SKUs"] = 0
  df_diario["SAUDAVEL"] = 0
  df_diario["BACKLOG"] = 0

# 3. Processamento do Faturamento (da aba DadosFaturamento)
if df_fat is not None:
  df_f = df_fat.copy()
  df_f["DATA"] = pd.to_datetime(df_f["DATA"], errors="coerce")

  # Detecta o nome da coluna de Faturamento
  col_fat_nome = (
      "Vlr Faturado"
      if "Vlr Faturado" in df_f.columns
      else ("Faturamento" if "Faturamento" in df_f.columns else df_f.columns[1])
  )

  df_f.rename(columns={col_fat_nome: "Valor_Faturado"}, inplace=True)
  df_diario = pd.merge(
      df_diario, df_f[["DATA", "Valor_Faturado"]], on="DATA", how="left"
  ).fillna(0)
else:
  df_diario["Valor_Faturado"] = 0.0

# 4. Expedição (Romaneios)
df_r = df_rom_tratado.copy()
df_r["DATA"] = pd.to_datetime(df_r["Dt. Romaneio"], errors="coerce")
df_r.rename(columns={"Qtd. Expedição": "Total_Expedidos"}, inplace=True)

df_diario = pd.merge(
    df_diario, df_r[["DATA", "Total_Expedidos"]], on="DATA", how="outer"
).fillna(0)
df_diario = df_diario.sort_values("DATA").reset_index(drop=True)
df_diario["Data_Str"] = df_diario["DATA"].dt.strftime("%Y-%m-%d")

# --- KPIs PRINCIPAIS ---
kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)

total_pvs = int(df_diario["Total_PVs"].sum())
total_saudavel = int(df_diario["SAUDAVEL"].sum())
total_backlog = int(df_diario["BACKLOG"].sum())
total_skus = int(df_diario["Total_SKUs"].sum())
total_faturado = df_diario["Valor_Faturado"].sum()

with kpi1:
  st.metric(
      label="📄 Total PVs Produzidos",
      value=total_pvs,
      delta=f"Média: {df_diario['Total_PVs'].mean():.1f}/dia",
  )
with kpi2:
  st.metric(
      label="✅ Notas Saudáveis",
      value=total_saudavel,
      delta=(
          f"{(total_saudavel/total_pvs*100):.1f}% do Total"
          if total_pvs > 0
          else "0%"
      ),
  )
with kpi3:
  st.metric(
      label="⚠️ Backlog",
      value=total_backlog,
      delta=(
          f"{(total_backlog/total_pvs*100):.1f}% do Total"
          if total_pvs > 0
          else "0%"
      ),
      delta_color="inverse",
  )
with kpi4:
  st.metric(
      label="📦 Total SKUs Produzidos",
      value=total_skus,
      delta=f"Média: {df_diario['Total_SKUs'].mean():.1f}/dia",
  )
with kpi5:
  st.metric(
      label="💰 Total Faturado",
      value=f"R$ {total_faturado:,.2f}".replace(",", "X")
      .replace(".", ",")
      .replace("X", "."),
  )

st.markdown("")

# --- GRÁFICO 1: PRODUÇÃO VS VALOR FATURADO ---
st.subheader("💵 Produção Diária: Pedidos de Venda (PV) vs. Valor Faturado (R$)")

fig_fat = go.Figure()

fig_fat.add_trace(
    go.Bar(
        x=df_diario["Data_Str"],
        y=df_diario["Total_PVs"],
        name="Pedidos de Venda (PV)",
        marker_color="#00b4d8",
        text=df_diario["Total_PVs"].astype(int),
        textposition="auto",
        yaxis="y1",
    )
)

fat_labels = [f"R$ {v:,.0f}".replace(",", ".") for v in df_diario["Valor_Faturado"]]

fig_fat.add_trace(
    go.Scatter(
        x=df_diario["Data_Str"],
        y=df_diario["Valor_Faturado"],
        name="Valor Faturado (R$)",
        mode="lines+markers+text",
        text=fat_labels,
        textposition="top center",
        marker_color="#52b788",
        line=dict(width=3),
        yaxis="y2",
    )
)

fig_fat.update_layout(
    template="plotly_dark",
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="right", x=1),
    xaxis=dict(title="Data", type="category"),
    yaxis=dict(
        title=dict(
            text="<b>Qtd de Pedidos (PV)</b>", font=dict(color="#00b4d8")
        )
    ),
    yaxis2=dict(
        title=dict(
            text="<b>Valor Faturado (R$)</b>", font=dict(color="#52b788")
        ),
        overlaying="y",
        side="right",
        showgrid=False,
    ),
    margin=dict(l=40, r=40, t=50, b=40),
)

st.plotly_chart(fig_fat, use_container_width=True)

# --- GRÁFICO 2: PRODUÇÃO VS SKUs ---
st.subheader("📊 Produção Diária: Pedidos de Venda (PV) vs. SKUs")

fig_unificado = go.Figure()
fig_unificado.add_trace(
    go.Bar(
        x=df_diario["Data_Str"],
        y=df_diario["Total_PVs"],
        name="Pedidos de Venda (PV)",
        marker_color="#48cae4",
        text=df_diario["Total_PVs"].astype(int),
        textposition="auto",
        yaxis="y1",
    )
)
fig_unificado.add_trace(
    go.Scatter(
        x=df_diario["Data_Str"],
        y=df_diario["Total_SKUs"],
        name="Total de SKUs",
        mode="lines+markers+text",
        text=df_diario["Total_SKUs"].astype(int),
        textposition="top center",
        marker_color="#f77f00",
        line=dict(width=3),
        yaxis="y2",
    )
)
fig_unificado.update_layout(
    template="plotly_dark",
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="right", x=1),
    xaxis=dict(title="Data", type="category"),
    yaxis=dict(
        title=dict(
            text="<b>Qtd de Pedidos (PV)</b>", font=dict(color="#48cae4")
        )
    ),
    yaxis2=dict(
        title=dict(text="<b>Total de SKUs</b>", font=dict(color="#f77f00")),
        overlaying="y",
        side="right",
        showgrid=False,
    ),
    margin=dict(l=40, r=40, t=50, b=40),
)
st.plotly_chart(fig_unificado, use_container_width=True)

# --- GRÁFICO 3: PRODUÇÃO ISOLADA (SAUDÁVEL VS BACKLOG) ---
st.subheader("📋 Produção Diária Isolada: Notas Saudáveis vs. Backlog")

fig_status_isolado = go.Figure()
fig_status_isolado.add_trace(
    go.Bar(
        x=df_diario["Data_Str"],
        y=df_diario["SAUDAVEL"],
        name="Notas Saudáveis",
        marker_color="#2a9d8f",
        text=df_diario["SAUDAVEL"].astype(int),
        textposition="auto",
    )
)
fig_status_isolado.add_trace(
    go.Bar(
        x=df_diario["Data_Str"],
        y=df_diario["BACKLOG"],
        name="Backlog",
        marker_color="#e76f51",
        text=df_diario["BACKLOG"].astype(int),
        textposition="auto",
    )
)
fig_status_isolado.update_layout(
    barmode="stack",
    template="plotly_dark",
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="right", x=1),
    xaxis=dict(title="Data de Produção", type="category"),
    yaxis=dict(title="Quantidade de Pedidos (PV)"),
    margin=dict(l=40, r=40, t=50, b=40),
)
st.plotly_chart(fig_status_isolado, use_container_width=True)

# --- GRÁFICO 4: COMPARATIVO PRODUÇÃO X EXPEDIÇÃO ---
st.subheader("🚚 Comparativo: Pedidos Produzidos (PV) vs. Expedições")

fig_comp = go.Figure()
fig_comp.add_trace(
    go.Bar(
        x=df_diario["Data_Str"],
        y=df_diario["Total_PVs"],
        name="Produzidos no Dia",
        marker_color="#2a9d8f",
        text=df_diario["Total_PVs"].astype(int),
        textposition="auto",
    )
)
fig_comp.add_trace(
    go.Bar(
        x=df_diario["Data_Str"],
        y=df_diario["Total_Expedidos"],
        name="Expedidos no Dia (Romaneio)",
        marker_color="#e76f51",
        text=df_diario["Total_Expedidos"].astype(int),
        textposition="auto",
    )
)
fig_comp.update_layout(
    barmode="group",
    template="plotly_dark",
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="right", x=1),
    xaxis=dict(title="Data", type="category"),
    yaxis=dict(title="Quantidade"),
    margin=dict(l=40, r=40, t=50, b=40),
)
st.plotly_chart(fig_comp, use_container_width=True)

# --- MACHINE LEARNING ---
st.divider()
st.subheader("🤖 Modelo Preditivo de Machine Learning")

col_ml1, col_ml2 = st.columns(2)

with col_ml1:
  st.markdown("### 📈 Simulação de Capacidade de Expedição")
  input_saudavel = st.slider(
      "Meta de Notas Saudáveis:", 0, 150, int(df_diario["SAUDAVEL"].mean())
  )
  input_backlog = st.slider(
      "Meta de Backlog:", 0, 150, int(df_diario["BACKLOG"].mean())
  )
  input_skus = st.slider(
      "Estimativa de SKUs:", 50, 500, int(df_diario["Total_SKUs"].mean())
  )

  X = df_diario[["SAUDAVEL", "BACKLOG", "Total_SKUs"]]
  y = df_diario["Total_Expedidos"]

  if len(df_diario) >= 3:
    rf_model = RandomForestRegressor(n_estimators=100, random_state=42)
    rf_model.fit(X, y)

    pred_expedicao = rf_model.predict(
        [[input_saudavel, input_backlog, input_skus]]
    )[0]

    st.success(
        f"**Expedição Preditiva Estimada:** `{int(pred_expedicao)}` volumes /"
        " romaneios."
    )
  else:
    st.info("Dados insuficientes para treinamento do modelo.")

with col_ml2:
  st.markdown("### 📊 Estatísticas Diárias do Período")
  st.write(f"- **Média de Notas Saudáveis/dia:** `{df_diario['SAUDAVEL'].mean():.2f}`")
  st.write(f"- **Média de Backlog/dia:** `{df_diario['BACKLOG'].mean():.2f}`")
  st.write(f"- **Média Diária de SKUs:** `{df_diario['Total_SKUs'].mean():.2f}`")
  st.write(
      "- **Média de Faturamento/dia:**"
      f" `R$ {df_diario['Valor_Faturado'].mean():,.2f}`"
  )

# --- TABELA DETALHADA ---
with st.expander("🔍 Visualizar Tabela Consolidada"):
  st.dataframe(
      df_diario[[
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