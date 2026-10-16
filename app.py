import os
import pandas as pd
import plotly.express as px
import streamlit as st

# Configuração da página (deve ser a primeira linha Streamlit)
st.set_page_config(
    page_title="Dashboard - Operação Rambo", page_icon="📦", layout="wide"
)

# --- ESTILIZAÇÃO CSS CUSTOMIZADA (Tonalidade Azulada / Corporativa) ---
st.markdown(
    """
    <style>
    /* Cor de fundo principal e fontes */
    .main {
        background-color: #0b132b;
        color: #ffffff;
    }
    /* Estilização da barra lateral */
    [data-testid="stSidebar"] {
        background-color: #1c2541;
        color: #ffffff;
    }
    /* Cartões de métricas (KPIs) */
    [data-testid="stMetric"] {
        background-color: #1c2541;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #3a506b;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    [data-testid="stMetricLabel"] {
        color: #8da9c4 !important;
    }
    [data-testid="stMetricValue"] {
        color: #ffffff !important;
    }
    /* Títulos */
    h1, h2, h3 {
        color: #e0fbfc !important;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# --- CABEÇALHO E LOGOS ---
col_logo1, col_titulo, col_logo2 = st.columns([1, 4, 1])

with col_logo1:
  if os.path.exists("images.jpg"):
    st.image(
        "images.jpg", width=110, caption="Control Log"
    )  # Ajuste o nome se necessário

with col_titulo:
  st.title("📦 Dashboard de Produção - Operação Rambo")
  st.markdown(
      "Controle diário de **Notas Produzidas** e **Total de SKUs** por período."
  )

with col_logo2:
  if os.path.exists("logo2.png"):
    st.image("logo2.png", width=130, caption="Higimed")  # Ajuste o nome se necessário

st.divider()

# --- CARREGAMENTO DOS DADOS ---
file_path = "Operação Rambo (1) (1).xlsx"


@st.cache_data
def load_data(path):
  try:
    return pd.read_excel(path)
  except Exception:
    return None


df = load_data(file_path)

if df is None:
  st.error(
      "A planilha padrão não foi encontrada. Faça o upload do arquivo Excel"
      " abaixo:"
  )
  uploaded_file = st.file_uploader(
      "Envie sua planilha (.xlsx)", type=["xlsx"]
  )
  if uploaded_file is not None:
    df = pd.read_excel(uploaded_file)
  else:
    st.stop()

# --- BARRA LATERAL (FILTROS) ---
st.sidebar.header("⚙️ Filtros e Parâmetros")

colunas_disponiveis = df.columns.tolist()

# Seleção automática ou manual das colunas essenciais
col_data = st.sidebar.selectbox(
    "Coluna de Data",
    colunas_disponiveis,
    index=(
        colunas_disponiveis.index("DATA")
        if "DATA" in colunas_disponiveis
        else 0
    ),
)
col_nota = st.sidebar.selectbox(
    "Coluna de Notas",
    colunas_disponiveis,
    index=(
        colunas_disponiveis.index("NF")
        if "NF" in colunas_disponiveis
        else min(1, len(colunas_disponiveis) - 1)
    ),
)
col_sku = st.sidebar.selectbox(
    "Coluna de SKUs",
    colunas_disponiveis,
    index=(
        colunas_disponiveis.index("SKU'S")
        if "SKU'S" in colunas_disponiveis
        else min(4, len(colunas_disponiveis) - 1)
    ),
)

# Tratamento das datas
df[col_data] = pd.to_datetime(df[col_data], errors="coerce")
df = df.dropna(subset=[col_data])

# Criar referência de semana no formato Ano - Semana
df["Ano_Semana"] = df[col_data].dt.strftime("%Y - Semana %V")

# Filtro por Semanas
semanas_disponiveis = sorted(df["Ano_Semana"].unique(), reverse=True)
semanas_selecionadas = st.sidebar.multiselect(
    "Filtrar por Semana(s)",
    options=semanas_disponiveis,
    default=semanas_disponiveis,
)

# Filtragem do DataFrame
if semanas_selecionadas:
  df_filtrado = df[df["Ano_Semana"].isin(semanas_selecionadas)]
else:
  df_filtrado = df

# --- AGRUPAMENTO DOS DADOS DIÁRIOS ---
df_diario = (
    df_filtrado.groupby(df_filtrado[col_data].dt.date)
    .agg(
        Total_Notas=(
            col_nota,
            "nunique",
        ),  # Contagem única de notas por dia
        Total_SKUs=(
            col_sku,
            "sum",
        ),  # Soma dos SKUs produzidos no dia
    )
    .reset_index()
)
df_diario.rename(columns={col_data: "Data"}, inplace=True)

# --- KPIs (MÉTRICAS PRINCIPAIS) ---
col_kpi1, col_kpi2 = st.columns(2)
with col_kpi1:
  st.metric(
      label="📄 Total de Notas no Período",
      value=int(df_diario["Total_Notas"].sum()),
  )
with col_kpi2:
  st.metric(
      label="📦 Total de SKUs no Período",
      value=int(df_diario["Total_SKUs"].sum()),
  )

st.markdown("")

# --- GRÁFICOS COM PLOTLY (Tema Escuro / Azulado) ---
# 1. Gráfico de Notas Produzidas por Dia
fig_notas = px.bar(
    df_diario,
    x="Data",
    y="Total_Notas",
    title="<b>Quantidade de Notas Produzidas por Dia</b>",
    labels={"Total_Notas": "Qtd de Notas", "Data": "Data da Produção"},
    text_auto=True,
    template="plotly_dark",
    color_discrete_sequence=["#48cae4"],
)
fig_notas.update_layout(
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    xaxis_title="Data",
    yaxis_title="Total de Notas",
)
st.plotly_chart(fig_notas, use_container_width=True)

# 2. Gráfico de Total de SKUs por Dia
fig_skus = px.line(
    df_diario,
    x="Data",
    y="Total_SKUs",
    title="<b>Total de SKUs por Dia</b>",
    labels={"Total_SKUs": "Soma de SKUs", "Data": "Data da Produção"},
    markers=True,
    template="plotly_dark",
    color_discrete_sequence=["#00b4d8"],
)
fig_skus.update_layout(
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    xaxis_title="Data",
    yaxis_title="Total de SKUs",
)
st.plotly_chart(fig_skus, use_container_width=True)

# --- TABELA DETALHADA ---
with st.expander("🔍 Visualizar Dados Tabulares Consolidados"):
  st.dataframe(df_diario, use_container_width=True)