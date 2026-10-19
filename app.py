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
        background-color: #f8f9fa;
        color: #000000 !important;
    }
    h1, h2, h3, h4, h5, h6 {
        color: #000000 !important;
        font-weight: 800 !important;
    }
    p, span, label, div, .stMarkdown {
        color: #000000 !important;
        font-weight: 600;
    }
    [data-testid="stSidebar"] {
        background-color: #e9ecef;
        color: #000000 !important;
    }
    [data-testid="stSidebar"] * {
        color: #000000 !important;
    }
    [data-testid="stMetric"] {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        border: 2px solid #ced4da;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    [data-testid="stMetricLabel"] {
        color: #000000 !important;
        font-weight: 700 !important;
        font-size: 1.1rem !important;
    }
    [data-testid="stMetricValue"] {
        color: #000000 !important;
        font-weight: 800 !important;
    }
    .streamlit-expanderHeader {
        color: #000000 !important;
        font-weight: 700 !important;
    }
    .logo-container {
        background-color: #ffffff;
        padding: 8px;
        border-radius: 10px;
        border: 1px solid #ced4da;
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
        '<div class="logo-container" style="background-color: #ffffff;">',
        unsafe_allow_html=True,
    )
    st.image("logo2.png", width=120)
    st.markdown("</div>", unsafe_allow_html=True)
  else:
    st.write("Higimed")

st.divider()

# --- UPLOAD DE ARQUIVOS ---
st.sidebar.header("📁 Upload de Arquivos")
uploaded_prod = st.sidebar.file_uploader(
    "Planilha de Produção (.xlsx)", type=["xlsx"]
)
uploaded_rom = st.sidebar.file_uploader(
    "Planilha de Romaneios (.xlsx)", type=["xlsx"]
)
uploaded_fat = st.sidebar.file_uploader(
    "Planilha de Faturamento (.xlsx)", type=["xlsx"]
)


@st.cache_data
def load_data(file_p, file_r, file_f):
  df_prod_bruto, df_prod_tratado = None, None
  df_rom_bruto, df_rom_tratado = None, None
  df_fat_detalhado = None

  # 1. Produção
  file_p_path = file_p if file_p is not None else "DadosProducao.xlsx"
  if os.path.exists(file_p_path) or file_p is not None:
    try:
      df_prod_bruto = pd.read_excel(file_p_path, sheet_name="DadosBrutos")
      df_prod_tratado = pd.read_excel(file_p_path, sheet_name="LimpezaDados")
    except Exception as e:
      st.error(f"Erro ao carregar Produção: {e}")

  # 2. Romaneios
  file_r_path = file_r if file_r is not None else "DadosRomaneios.xlsx"
  if os.path.exists(file_r_path) or file_r is not None:
    try:
      df_rom_bruto = pd.read_excel(file_r_path, sheet_name="Romaneios")
      df_rom_tratado = pd.read_excel(file_r_path, sheet_name="Planilha1")
    except Exception as e:
      st.error(f"Erro ao carregar Romaneios: {e}")

  # 3. Faturamento Detalhado
  if file_f is not None:
    try:
      df_fat_detalhado = pd.read_excel(file_f)
    except Exception as e:
      st.error(f"Erro ao carregar Faturamento: {e}")
  elif os.path.exists("DadosFaturamento.xlsx"):
    try:
      df_fat_detalhado = pd.read_excel("DadosFaturamento.xlsx")
    except Exception as e:
      st.error(f"Erro ao carregar DadosFaturamento.xlsx local: {e}")

  return df_prod_bruto, df_prod_tratado, df_rom_bruto, df_rom_tratado, df_fat_detalhado


(
    df_prod_bruto,
    df_prod_tratado,
    df_rom_bruto,
    df_rom_tratado,
    df_fat_detalhado,
) = load_data(uploaded_prod, uploaded_rom, uploaded_fat)

if df_prod_tratado is None or df_rom_tratado is None:
  st.warning("Por favor, faça o upload das planilhas na barra lateral para iniciar.")
  st.stop()

# --- CONSOLIDAÇÃO OPERACIONAL EXCLUSIVA (PRODUÇÃO & ROMANEIOS) ---
df_p = df_prod_tratado.copy()
df_p["DATA"] = pd.to_datetime(df_p["DATA"], errors="coerce")
df_p.rename(columns={"Quantidade": "Total_PVs"}, inplace=True)

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

# Romaneios
df_r = df_rom_tratado.copy()
df_r["DATA"] = pd.to_datetime(df_r["Dt. Romaneio"], errors="coerce")
df_r.rename(columns={"Qtd. Expedição": "Total_Expedidos"}, inplace=True)

# Merge apenas entre Produção e Romaneios (série operacional)
df_diario = pd.merge(
    df_diario, df_r[["DATA", "Total_Expedidos"]], on="DATA", how="outer"
).fillna(0)

# Faturamento cruzado APENAS para as datas operacionais
if df_fat_detalhado is not None:
  df_fd_calc = df_fat_detalhado.copy()
  col_emissao_calc = (
      "Emissão"
      if "Emissão" in df_fd_calc.columns
      else ("DATA" if "DATA" in df_fd_calc.columns else df_fd_calc.columns[1])
  )
  col_valor_calc = (
      "Valor"
      if "Valor" in df_fd_calc.columns
      else (
          "Vlr Faturado"
          if "Vlr Faturado" in df_fd_calc.columns
          else df_fd_calc.columns[-1]
      )
  )

  df_fd_calc["DATA"] = pd.to_datetime(
      df_fd_calc[col_emissao_calc], errors="coerce"
  )
  df_fat_diario_agg = (
      df_fd_calc.groupby("DATA")[col_valor_calc]
      .sum()
      .reset_index(name="Valor_Faturado")
  )

  # HOW='LEFT' para NÃO incluir datas exclusivas da planilha de faturamento nos gráficos operacionais
  df_diario = pd.merge(df_diario, df_fat_diario_agg, on="DATA", how="left").fillna(
      0
  )
else:
  df_diario["Valor_Faturado"] = 0.0

df_diario = df_diario.sort_values("DATA").reset_index(drop=True)
df_diario["Data_Str"] = df_diario["DATA"].dt.strftime("%Y-%m-%d")

# Layout Padrão dos Gráficos
layout_graficos = dict(
    template="plotly_white",
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#000000", size=13, family="Arial"),
    title_font=dict(color="#000000", size=16, family="Arial Black"),
    xaxis=dict(
        title=dict(font=dict(size=14, color="#000000")),
        tickfont=dict(color="#000000", size=12, family="Arial"),
        type="category",
    ),
    yaxis=dict(
        title=dict(font=dict(size=14, color="#000000")),
        tickfont=dict(color="#000000", size=12, family="Arial"),
        gridcolor="#dee2e6",
    ),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.05,
        xanchor="right",
        x=1,
        font=dict(size=12, color="#000000"),
    ),
    margin=dict(l=40, r=40, t=50, b=40),
)

# --- KPIs PRINCIPAIS ---
kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)

total_pvs = int(df_diario["Total_PVs"].sum())
total_saudavel = int(df_diario["SAUDAVEL"].sum())
total_backlog = int(df_diario["BACKLOG"].sum())
total_skus = int(df_diario["Total_SKUs"].sum())
total_faturado = (
    df_fat_detalhado[
        "Valor"
        if "Valor" in df_fat_detalhado.columns
        else df_fat_detalhado.columns[-1]
    ].sum()
    if df_fat_detalhado is not None
    else 0.0
)

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
      label="💰 Total Faturado Real",
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
        marker=dict(color="#0077b6", line=dict(color="#000000", width=1)),
        text=[f"<b>{int(v)}</b>" for v in df_diario["Total_PVs"]],
        textfont=dict(color="#ffffff", size=13),
        textangle=0,
        textposition="auto",
        cliponaxis=False,
        yaxis="y1",
    )
)

fat_labels = [
    f"<b>R$ {v:,.0f}</b>".replace(",", ".")
    for v in df_diario["Valor_Faturado"]
]

fig_fat.add_trace(
    go.Scatter(
        x=df_diario["Data_Str"],
        y=df_diario["Valor_Faturado"],
        name="Valor Faturado (R$)",
        mode="lines+markers+text",
        text=fat_labels,
        textfont=dict(color="#000000", size=13),
        textposition="top center",
        marker=dict(color="#2ec4b6", size=9),
        line=dict(color="#2ec4b6", width=4),
        yaxis="y2",
    )
)

fig_fat.update_layout(**layout_graficos)
fig_fat.update_layout(
    yaxis=dict(
        title=dict(
            text="<b>Qtd de Pedidos (PV)</b>",
            font=dict(color="#0077b6", size=14),
        ),
        tickfont=dict(color="#000000", size=12),
    ),
    yaxis2=dict(
        title=dict(
            text="<b>Valor Faturado (R$)</b>",
            font=dict(color="#00a896", size=14),
        ),
        tickfont=dict(color="#000000", size=12),
        overlaying="y",
        side="right",
        showgrid=False,
    ),
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
        marker=dict(color="#0077b6", line=dict(color="#000000", width=1)),
        text=[f"<b>{int(v)}</b>" for v in df_diario["Total_PVs"]],
        textfont=dict(color="#ffffff", size=13),
        textangle=0,
        textposition="auto",
        cliponaxis=False,
        yaxis="y1",
    )
)
fig_unificado.add_trace(
    go.Scatter(
        x=df_diario["Data_Str"],
        y=df_diario["Total_SKUs"],
        name="Total de SKUs",
        mode="lines+markers+text",
        text=[f"<b>{int(v)}</b>" for v in df_diario["Total_SKUs"]],
        textfont=dict(color="#000000", size=13),
        textposition="top center",
        marker=dict(color="#d97706", size=9),
        line=dict(color="#d97706", width=4),
        yaxis="y2",
    )
)
fig_unificado.update_layout(**layout_graficos)
fig_unificado.update_layout(
    yaxis=dict(
        title=dict(
            text="<b>Qtd de Pedidos (PV)</b>",
            font=dict(color="#0077b6", size=14),
        ),
        tickfont=dict(color="#000000", size=12),
    ),
    yaxis2=dict(
        title=dict(
            text="<b>Total de SKUs</b>", font=dict(color="#d97706", size=14)
        ),
        tickfont=dict(color="#000000", size=12),
        overlaying="y",
        side="right",
        showgrid=False,
    ),
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
        marker=dict(color="#0f9f90", line=dict(color="#000000", width=1)),
        text=[f"<b>{int(v)}</b>" if v > 0 else "" for v in df_diario["SAUDAVEL"]],
        textfont=dict(color="#ffffff", size=13),
        textangle=0,
        textposition="auto",
        cliponaxis=False,
    )
)
fig_status_isolado.add_trace(
    go.Bar(
        x=df_diario["Data_Str"],
        y=df_diario["BACKLOG"],
        name="Backlog",
        marker=dict(color="#d9381e", line=dict(color="#000000", width=1)),
        text=[f"<b>{int(v)}</b>" if v > 0 else "" for v in df_diario["BACKLOG"]],
        textfont=dict(color="#ffffff", size=13),
        textangle=0,
        textposition="auto",
        cliponaxis=False,
    )
)
fig_status_isolado.update_layout(**layout_graficos)
fig_status_isolado.update_layout(
    barmode="stack", yaxis=dict(title="<b>Quantidade de Pedidos (PV)</b>")
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
        marker=dict(color="#0f9f90", line=dict(color="#000000", width=1)),
        text=[f"<b>{int(v)}</b>" for v in df_diario["Total_PVs"]],
        textfont=dict(color="#ffffff", size=13),
        textangle=0,
        textposition="auto",
        cliponaxis=False,
    )
)
fig_comp.add_trace(
    go.Bar(
        x=df_diario["Data_Str"],
        y=df_diario["Total_Expedidos"],
        name="Expedidos no Dia (Romaneio)",
        marker=dict(color="#d9381e", line=dict(color="#000000", width=1)),
        text=[f"<b>{int(v)}</b>" for v in df_diario["Total_Expedidos"]],
        textfont=dict(color="#ffffff", size=13),
        textangle=0,
        textposition="auto",
        cliponaxis=False,
    )
)
fig_comp.update_layout(**layout_graficos)
fig_comp.update_layout(barmode="group", yaxis=dict(title="<b>Quantidade</b>"))
st.plotly_chart(fig_comp, use_container_width=True)

# --- RANKING DIÁRIO DE PRODUÇÃO POR CLIENTE (TOP 5 PVS) ---
st.divider()
st.subheader("🏆 Top 5 Clientes por Pedidos de Venda (PVs Produzidos)")

if (
    df_prod_bruto is not None
    and "CLIENTE" in df_prod_bruto.columns
    and "PV" in df_prod_bruto.columns
):
  df_pb_cliente = df_prod_bruto.copy()
  df_pb_cliente["DATA_STR"] = pd.to_datetime(
      df_pb_cliente["DATA"], errors="coerce"
  ).dt.strftime("%Y-%m-%d")
  datas_prod_disponiveis = sorted(df_pb_cliente["DATA_STR"].dropna().unique())

  data_prod_sel = st.selectbox(
      "Selecione a Data para visualizar o Top 5 PVs:",
      datas_prod_disponiveis,
      index=len(datas_prod_disponiveis) - 1,
      key="sel_prod_pv",
  )

  df_top_dia = df_pb_cliente[df_pb_cliente["DATA_STR"] == data_prod_sel]
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
            marker=dict(color="#3a86ff", line=dict(color="#000000", width=1)),
            text=[f"<b>{int(v)} PVs</b>" for v in df_ranking_pv["Qtd_PVs"]],
            textfont=dict(color="#ffffff", size=12),
            textangle=0,
            textposition="auto",
            cliponaxis=False,
        )
    )
    fig_top_pv.update_layout(**layout_graficos)
    fig_top_pv.update_layout(
        xaxis=dict(
            title=dict(text="<b>Qtd. Pedidos de Venda (PV)</b>"), type="linear"
        ),
        yaxis=dict(title=dict(text="<b>Cliente</b>")),
        margin=dict(l=180, r=40, t=30, b=40),
    )
    st.plotly_chart(fig_top_pv, use_container_width=True)

# --- RANKING EXPANDIDO TOP 10 FATURAMENTO ---
st.divider()
st.subheader("💎 Ranking Top 10 Clientes por Faturamento Monetário (R$)")

if df_fat_detalhado is not None:
  df_fd10 = df_fat_detalhado.copy()

  col_cli = (
      "Nome Fantasia"
      if "Nome Fantasia" in df_fd10.columns
      else ("CLIENTE" if "CLIENTE" in df_fd10.columns else df_fd10.columns[2])
  )
  col_emissao = (
      "Emissão"
      if "Emissão" in df_fd10.columns
      else ("DATA" if "DATA" in df_fd10.columns else df_fd10.columns[1])
  )
  col_valor = (
      "Valor"
      if "Valor" in df_fd10.columns
      else (
          "Vlr Faturado"
          if "Vlr Faturado" in df_fd10.columns
          else df_fd10.columns[-1]
      )
  )

  df_fd10["DATA_STR"] = pd.to_datetime(
      df_fd10[col_emissao], errors="coerce"
  ).dt.strftime("%Y-%m-%d")
  datas_fat_disponiveis10 = sorted(df_fd10["DATA_STR"].dropna().unique())

  col_mode, col_date_top10 = st.columns([2, 2])

  with col_mode:
    modo_top10 = st.radio(
        "Modo de Exibição do Top 10:",
        ["Por Dia Selecionado", "Acumulado do Período Geral"],
        horizontal=True,
    )

  if modo_top10 == "Por Dia Selecionado":
    with col_date_top10:
      data_top10_sel = st.selectbox(
          "Selecione a Data de Emissão (Faturamento):",
          datas_fat_disponiveis10,
          index=len(datas_fat_disponiveis10) - 1,
          key="sel_fat_10",
      )
    df_top10_filtrado = df_fd10[df_fd10["DATA_STR"] == data_top10_sel]
    titulo_top10 = f"Top 10 Clientes por Faturamento no Dia: {data_top10_sel}"
  else:
    df_top10_filtrado = df_fd10
    titulo_top10 = "Top 10 Clientes por Faturamento Acumulado no Período"

  df_top10 = (
      df_top10_filtrado.groupby(col_cli)[col_valor]
      .sum()
      .reset_index(name="Total_Faturado")
      .sort_values("Total_Faturado", ascending=False)
      .head(10)
  )
  df_top10 = df_top10.sort_values("Total_Faturado", ascending=True)

  if not df_top10.empty:
    labels_top10 = [
        f"<b>R$ {v:,.2f}</b>".replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
        for v in df_top10["Total_Faturado"]
    ]

    fig_top10 = go.Figure()
    fig_top10.add_trace(
        go.Bar(
            y=df_top10[col_cli],
            x=df_top10["Total_Faturado"],
            orientation="h",
            marker=dict(color="#118ab2", line=dict(color="#000000", width=1)),
            text=labels_top10,
            textfont=dict(color="#ffffff", size=12),
            textangle=0,
            textposition="auto",
            cliponaxis=False,
        )
    )
    fig_top10.update_layout(**layout_graficos)
    fig_top10.update_layout(
        title=dict(text=f"<b>{titulo_top10}</b>"),
        xaxis=dict(
            title=dict(text="<b>Valor Faturado Total (R$)</b>"), type="linear"
        ),
        yaxis=dict(title=dict(text="<b>Cliente</b>")),
        margin=dict(l=180, r=40, t=50, b=40),
    )
    st.plotly_chart(fig_top10, use_container_width=True)

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
  st.write(
      f"- **Média de Notas Saudáveis/dia:** `{df_diario['SAUDAVEL'].mean():.2f}`"
  )
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