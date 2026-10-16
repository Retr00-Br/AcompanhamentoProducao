import os
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

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
      "Controle diário de **Produção/Notas**, **SKUs** e **Expedição"
      " (Romaneios)**."
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
  df_prod, df_rom = None, None

  if file_p is not None:
    df_prod = pd.read_excel(file_p, sheet_name="SEPARAÇÃO")
  elif os.path.exists("Operação Rambo (1) (1).xlsx"):
    df_prod = pd.read_excel(
        "Operação Rambo (1) (1).xlsx", sheet_name="SEPARAÇÃO"
    )

  if file_r is not None:
    df_rom = pd.read_excel(file_r, header=0)
  elif os.path.exists("DadosRomaneios.xlsx"):
    df_rom = pd.read_excel("DadosRomaneios.xlsx", header=0)

  return df_prod, df_rom


df, df_rom = load_data(uploaded_prod, uploaded_rom)

if df is None:
  st.warning(
      "Por favor, faça o upload da planilha de produção na barra lateral para"
      " iniciar."
  )
  st.stop()

# --- BARRA LATERAL (FILTROS) ---
st.sidebar.header("⚙️ Filtros e Parâmetros")

colunas_disponiveis = df.columns.tolist()

col_data = st.sidebar.selectbox(
    "Coluna de Data",
    colunas_disponiveis,
    index=(
        colunas_disponiveis.index("DATA")
        if "DATA" in colunas_disponiveis
        else 0
    ),
)
# Usar PV ou ID de linha como padrão se NF estiver em branco
col_nota = st.sidebar.selectbox(
    "Coluna de Referência (Notas/Pedidos)",
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

# Tratamento da data de produção
df[col_data] = pd.to_datetime(df[col_data], errors="coerce")
df = df.dropna(subset=[col_data])
df["Ano_Semana"] = df[col_data].dt.strftime("%Y - Semana %V")

# Filtro de Semanas
semanas_disponiveis = sorted(df["Ano_Semana"].unique(), reverse=True)
semanas_selecionadas = st.sidebar.multiselect(
    "Filtrar por Semana(s)",
    options=semanas_disponiveis,
    default=semanas_disponiveis,
)

# Filtro de Separadores
separadores_disponiveis = (
    sorted(df["SEPARADOR"].dropna().astype(str).unique())
    if "SEPARADOR" in df.columns
    else []
)
separadores_selecionados = st.sidebar.multiselect(
    "Filtrar por Separador(es)",
    options=separadores_disponiveis,
    default=separadores_disponiveis,
)

# Aplicando Filtros
df_filtrado = df.copy()
if semanas_selecionadas:
  df_filtrado = df_filtrado[df_filtrado["Ano_Semana"].isin(semanas_selecionadas)]
if separadores_selecionados and "SEPARADOR" in df.columns:
  df_filtrado = df_filtrado[
      df_filtrado["SEPARADOR"].astype(str).isin(separadores_selecionados)
  ]

# --- PROCESSAMENTO DOS DADOS DIÁRIOS DE PRODUÇÃO ---
# Contamos registros válidos (linhas de pedidos/produção) para garantir contagem correta mesmo sem NF emitida
df_diario = (
    df_filtrado.groupby(df_filtrado[col_data].dt.date)
    .agg(
        Total_Notas=(
            col_nota,
            "count",
        ),  # Mudado para 'count' para englobar todas as produções diárias
        Total_SKUs=(col_sku, "sum"),
    )
    .reset_index()
)
df_diario.rename(columns={col_data: "Data"}, inplace=True)

# --- PROCESSAMENTO DOS ROMANEIOS (EXPEDIÇÃO) ---
if df_rom is not None and not df_rom.empty:
  col_dt_rom = (
      "Dt. Romaneio" if "Dt. Romaneio" in df_rom.columns else df_rom.columns[0]
  )
  col_nf_rom = "Num.NF" if "Num.NF" in df_rom.columns else df_rom.columns[6]

  df_rom["DATA_ROM"] = pd.to_datetime(df_rom[col_dt_rom], errors="coerce")
  df_rom = df_rom.dropna(subset=["DATA_ROM"])
  df_rom_diario = (
      df_rom.groupby(df_rom["DATA_ROM"].dt.date)
      .agg(Total_Romaneios=(col_nf_rom, "nunique"))
      .reset_index()
  )
  df_rom_diario.rename(columns={"DATA_ROM": "Data"}, inplace=True)

  df_diario = pd.merge(df_diario, df_rom_diario, on="Data", how="outer").fillna(
      0
  )
  df_diario = df_diario.sort_values("Data").reset_index(drop=True)
else:
  df_diario["Total_Romaneios"] = 0

# --- KPIs PRINCIPAIS ---
kpi1, kpi2, kpi3 = st.columns(3)
with kpi1:
  st.metric(
      label="📄 Total de Produção/Notas",
      value=int(df_diario["Total_Notas"].sum()),
  )
with kpi2:
  st.metric(
      label="📦 Total de SKUs Produzidos",
      value=int(df_diario["Total_SKUs"].sum()),
  )
with kpi3:
  st.metric(
      label="🚚 Total de Notas em Romaneios",
      value=int(df_diario["Total_Romaneios"].sum()),
  )

st.markdown("")

# --- GRÁFICO 1: UNIFICADO (Notas Produzidas x SKUs - Eixo Duplo) ---
st.subheader("📊 Produção Diária: Notas vs. SKUs")

fig_unificado = go.Figure()

fig_unificado.add_trace(
    go.Bar(
        x=df_diario["Data"],
        y=df_diario["Total_Notas"],
        name="Produção / Notas",
        marker_color="#48cae4",
        yaxis="y1",
    )
)

fig_unificado.add_trace(
    go.Scatter(
        x=df_diario["Data"],
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
    xaxis=dict(title="Data"),
    yaxis=dict(
        title=dict(
            text="<b>Quantidade de Produção/Notas</b>", font=dict(color="#48cae4")
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


# --- GRÁFICO 2: COMPARATIVO (Notas Produzidas vs. Notas em Romaneios / Expedição) ---
st.subheader(
    "🚚 Comparativo: Produção/Notas vs. Notas em Romaneios (Expedição)"
)

fig_comp = go.Figure()

fig_comp.add_trace(
    go.Bar(
        x=df_diario["Data"],
        y=df_diario["Total_Notas"],
        name="Produção / Notas",
        marker_color="#2a9d8f",
    )
)

fig_comp.add_trace(
    go.Bar(
        x=df_diario["Data"],
        y=df_diario["Total_Romaneios"],
        name="Notas em Romaneios (Expedição)",
        marker_color="#e76f51",
    )
)

fig_comp.update_layout(
    barmode="group",
    template="plotly_dark",
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    xaxis=dict(title="Data"),
    yaxis=dict(title="Quantidade"),
    margin=dict(l=40, r=40, t=40, b=40),
)

st.plotly_chart(fig_comp, use_container_width=True)

# --- TABELA DETALHADA ---
with st.expander("🔍 Visualizar Dados Tabulares Consolidados"):
  st.dataframe(df_diario, use_container_width=True)