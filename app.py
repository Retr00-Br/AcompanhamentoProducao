import os
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression

# Configuração da página
st.set_page_config(
    page_title="Dashboard - Dados da Logística", page_icon="📦", layout="wide"
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
  st.title("Dashboard de Produção - Operação Rambo")
  st.markdown(
      "Controle diário baseado em **Pedidos de Venda (PV)**, **SKUs** e"
      " **Expedição (Romaneios)** com Modelos Preditivos de ML."
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

# --- UPLOAD DINÂMICO DE ARQUIVOS ---
st.sidebar.header("📁 Upload de Planilhas Atualizadas")
uploaded_prod = st.sidebar.file_uploader(
    "Envie a planilha de Produção (.xlsx)", type=["xlsx"]
)
uploaded_rom = st.sidebar.file_uploader(
    "Envie a planilha de Romaneios (.xlsx)", type=["xlsx"]
)


@st.cache_data
def load_data(file_p, file_r):
  df_prod_bruto, df_prod_tratado = None, None
  df_rom_bruto, df_rom_tratado = None, None

  # 1. Leitura Produção
  file_p_path = file_p if file_p is not None else "DadosProducao.xlsx"
  if os.path.exists(file_p_path) or file_p is not None:
    try:
      df_prod_bruto = pd.read_excel(file_p_path, sheet_name="DadosBrutos")
      df_prod_tratado = pd.read_excel(file_p_path, sheet_name="LimpezaDados")
    except Exception as e:
      st.error(f"Erro ao carregar dados de produção: {e}")

  # 2. Leitura Romaneios
  file_r_path = file_r if file_r is not None else "DadosRomaneios.xlsx"
  if os.path.exists(file_r_path) or file_r is not None:
    try:
      df_rom_bruto = pd.read_excel(file_r_path, sheet_name="Romaneios")
      df_rom_tratado = pd.read_excel(file_r_path, sheet_name="Planilha1")
    except Exception as e:
      st.error(f"Erro ao carregar dados de romaneios: {e}")

  return df_prod_bruto, df_prod_tratado, df_rom_bruto, df_rom_tratado


df_prod_bruto, df_prod_tratado, df_rom_bruto, df_rom_tratado = load_data(
    uploaded_prod, uploaded_rom
)

if df_prod_bruto is None and df_prod_tratado is None:
  st.warning(
      "Por favor, faça o upload das planilhas na barra lateral para iniciar."
  )
  st.stop()

# --- OPÇÃO DE SELEÇÃO DE FONTE DE DADOS ---
st.sidebar.header("⚙️ Fonte de Dados e Filtros")
fonte_dados = st.sidebar.radio(
    "Usar Dados de:",
    ("Página 2 (Tratados / Consolidados)", "Página 1 (Dados Brutos)"),
)

# --- CONSOLIDAÇÃO DOS DADOS DIÁRIOS ---
if fonte_dados == "Página 2 (Tratados / Consolidados)":
  # Produção Tratada
  df_p = df_prod_tratado.copy()
  df_p["DATA"] = pd.to_datetime(df_p["DATA"], errors="coerce")
  df_p.rename(columns={"Quantidade": "Total_PVs"}, inplace=True)

  # SKUs calculados a partir dos dados brutos para manter o cálculo de SKUs
  if df_prod_bruto is not None:
    df_sku_agg = (
        df_prod_bruto.groupby(pd.to_datetime(df_prod_bruto["DATA"]).dt.date)[
            "SKU'S"
        ]
        .sum()
        .reset_index(name="Total_SKUs")
    )
    df_sku_agg["DATA"] = pd.to_datetime(df_sku_agg["DATA"])
    df_diario = pd.merge(df_p, df_sku_agg, on="DATA", how="left").fillna(0)
  else:
    df_diario = df_p
    df_diario["Total_SKUs"] = 0

  # Romaneios Tratados
  if df_rom_tratado is not None:
    df_r = df_rom_tratado.copy()
    df_r["DATA"] = pd.to_datetime(df_r["Dt. Romaneio"], errors="coerce")
    df_r.rename(columns={"Qtd. Expedição": "Total_Expedidos"}, inplace=True)
    df_diario = pd.merge(
        df_diario,
        df_r[["DATA", "Total_Expedidos"]],
        on="DATA",
        how="outer",
    ).fillna(0)

else:
  # Dados Brutos (Página 1)
  df_p = df_prod_bruto.copy()
  df_p["DATA"] = pd.to_datetime(df_p["DATA"], errors="coerce")

  df_diario = (
      df_p.groupby(df_p["DATA"].dt.date)
      .agg(Total_PVs=("PV", "count"), Total_SKUs=("SKU'S", "sum"))
      .reset_index()
  )
  df_diario["DATA"] = pd.to_datetime(df_diario["DATA"])

  if df_rom_bruto is not None:
    df_r = df_rom_bruto.copy()
    df_r["DATA"] = pd.to_datetime(df_r["Dt. Romaneio"], errors="coerce")
    df_rom_agg = (
        df_r.groupby(df_r["DATA"].dt.date)
        .size()
        .reset_index(name="Total_Expedidos")
    )
    df_rom_agg["DATA"] = pd.to_datetime(df_rom_agg["DATA"])
    df_diario = pd.merge(df_diario, df_rom_agg, on="DATA", how="left").fillna(0)

df_diario = df_diario.sort_values("DATA").reset_index(drop=True)
df_diario["Data_Str"] = df_diario["DATA"].dt.strftime("%Y-%m-%d")

# --- KPIs PRINCIPAIS E MÉDIAS ---
kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)

media_pvs = df_diario["Total_PVs"].mean()
media_skus = df_diario["Total_SKUs"].mean()
media_exp = df_diario["Total_Expedidos"].mean()

with kpi1:
  st.metric(
      label="📄 Total PVs Produzidos",
      value=int(df_diario["Total_PVs"].sum()),
      delta=f"Média: {media_pvs:.1f}/dia",
  )
with kpi2:
  st.metric(
      label="📦 Total SKUs Produzidos",
      value=int(df_diario["Total_SKUs"].sum()),
      delta=f"Média: {media_skus:.1f}/dia",
  )
with kpi3:
  st.metric(
      label="🚚 Total Expedições",
      value=int(df_diario["Total_Expedidos"].sum()),
      delta=f"Média: {media_exp:.1f}/dia",
  )
with kpi4:
  st.metric(label="📊 Média SKUs/PV", value=f"{media_skus / media_pvs:.2f}" if media_pvs > 0 else "0")
with kpi5:
  st.metric(
      label="⚡ Eficiência Expedição",
      value=f"{(media_exp / media_pvs * 100):.1f}%" if media_pvs > 0 else "0%",
  )

st.markdown("")

# --- GRÁFICO 1: UNIFICADO (PVs x SKUs) ---
st.subheader("📊 Produção Diária: Pedidos de Venda (PV) vs. SKUs")

fig_unificado = go.Figure()

fig_unificado.add_trace(
    go.Bar(
        x=df_diario["Data_Str"],
        y=df_diario["Total_PVs"],
        name="Pedidos de Venda (PV)",
        marker_color="#48cae4",
        yaxis="y1",
    )
)

fig_unificado.add_trace(
    go.Scatter(
        x=df_diario["Data_Str"],
        y=df_diario["Total_SKUs"],
        name="Total de SKUs",
        mode="lines+markers",
        marker_color="#f77f00",
        line=dict(width=3),
        yaxis="y2",
    )
)

fig_unificado.update_layout(
    template="plotly_dark",
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    xaxis=dict(title="Data", type="category"),
    yaxis=dict(
        title=dict(
            text="<b>Qtd de Pedidos de Venda (PV)</b>",
            font=dict(color="#48cae4"),
        )
    ),
    yaxis2=dict(
        title=dict(text="<b>Total de SKUs</b>", font=dict(color="#f77f00")),
        overlaying="y",
        side="right",
        showgrid=False,
    ),
    margin=dict(l=40, r=40, t=40, b=40),
)

st.plotly_chart(fig_unificado, use_container_width=True)

# --- GRÁFICO 2: COMPARATIVO PRODUÇÃO X EXPEDIÇÃO ---
st.subheader("🚚 Comparativo: Pedidos Produzidos (PV) vs. Expedições")

fig_comp = go.Figure()
fig_comp.add_trace(
    go.Bar(
        x=df_diario["Data_Str"],
        y=df_diario["Total_PVs"],
        name="Pedidos Produzidos (PV)",
        marker_color="#2a9d8f",
    )
)
fig_comp.add_trace(
    go.Bar(
        x=df_diario["Data_Str"],
        y=df_diario["Total_Expedidos"],
        name="Expedições (Romaneios)",
        marker_color="#e76f51",
    )
)
fig_comp.update_layout(
    barmode="group",
    template="plotly_dark",
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    xaxis=dict(title="Data", type="category"),
    yaxis=dict(title="Quantidade"),
    margin=dict(l=40, r=40, t=40, b=40),
)
st.plotly_chart(fig_comp, use_container_width=True)

# --- MÓDULO DE MACHINE LEARNING ---
st.divider()
st.subheader("🤖 Modelo de Machine Learning: Previsão de Expedição e Demanda de SKUs")

col_ml1, col_ml2 = st.columns(2)

with col_ml1:
  st.markdown("### 📈 Simulação de Capacidade de Expedição")
  input_pvs = st.slider("Selecione a meta de PVs produzidos no dia:", 10, 200, 80)
  input_skus = st.slider("Selecione a estimativa de SKUs movimentados:", 50, 500, 300)

  # Treinando o Modelo Random Forest Regressor
  X = df_diario[["Total_PVs", "Total_SKUs"]]
  y = df_diario["Total_Expedidos"]

  if len(df_diario) >= 3:
    rf_model = RandomForestRegressor(n_estimators=100, random_state=42)
    rf_model.fit(X, y)

    pred_expedicao = rf_model.predict([[input_pvs, input_skus]])[0]

    st.success(f"**Previsão de Expedição Estimada:** {int(pred_expedicao)} volumes / romaneios.")
    st.caption("Modelo treinado via Random Forest Regressor com os dados das planilhas.")
  else:
    st.info("Insira mais dados para habilitar o treinamento do modelo.")

with col_ml2:
  st.markdown("### 📊 Médias Históricas do Período")
  st.write(f"- **Média Diária de PVs:** `{media_pvs:.2f}`")
  st.write(f"- **Média Diária de SKUs:** `{media_skus:.2f}`")
  st.write(f"- **Média Diária de Expedições:** `{media_exp:.2f}`")
  st.write(f"- **Proporção Média de SKUs por PV:** `{media_skus/media_pvs:.2f}`")

# --- TABELA DETALHADA ---
with st.expander("🔍 Visualizar Tabela Consolidada"):
  st.dataframe(
      df_diario[["DATA", "Total_PVs", "Total_SKUs", "Total_Expedidos"]],
      use_container_width=True,
  )