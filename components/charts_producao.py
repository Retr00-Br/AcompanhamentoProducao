import pandas as pd
import plotly.graph_objects as go
import streamlit as st


def render_graficos_producao(df_filtrado: pd.DataFrame, col_fat_ativa: str, unidade_selecionada: str):
    if df_filtrado is None or df_filtrado.empty:
        st.info("Sem dados de produção para o período selecionado.")
        return

    df_p = df_filtrado.copy().sort_values("DATA").reset_index(drop=True)
    df_p["Data_Str"] = df_p["DATA"].dt.strftime("%d/%m")
    eixo_x = df_p["Data_Str"].tolist()

    # =========================================================================
    # 1. PRODUÇÃO DIÁRIA ISOLADA: NOTAS SAUDÁVEIS VS. BACKLOG
    # =========================================================================
    st.markdown("---")
    st.markdown("### 🏭 Produção Diária Isolada: Notas Saudáveis vs. Backlog")

    y_saud = df_p["Saudavel"].fillna(0).astype(int).tolist()
    y_back = df_p["Backlog"].fillna(0).astype(int).tolist()
    max_sb = max(max(y_saud, default=10), max(y_back, default=10))

    fig_sb = go.Figure()

    fig_sb.add_trace(
        go.Bar(
            x=eixo_x,
            y=y_saud,
            name="Notas Saudáveis",
            marker=dict(color="#2ca02c", line=dict(color="#000000", width=0.8)),
            text=[str(v) if v > 0 else "" for v in y_saud],
            textposition="outside",
            textfont=dict(size=11, color="#2ca02c", family="Arial Black"),
            cliponaxis=False,
            hovertemplate="<b>Data: %{x}</b><br>Notas Saudáveis: %{y}<extra></extra>",
        )
    )

    fig_sb.add_trace(
        go.Bar(
            x=eixo_x,
            y=y_back,
            name="Backlog",
            marker=dict(color="#d62728", line=dict(color="#000000", width=0.8)),
            text=[str(v) if v > 0 else "" for v in y_back],
            textposition="outside",
            textfont=dict(size=11, color="#d62728", family="Arial Black"),
            cliponaxis=False,
            hovertemplate="<b>Data: %{x}</b><br>Backlog: %{y}<extra></extra>",
        )
    )

    fig_sb.update_layout(
        template="plotly_white",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#000000", size=12, family="Arial"),
        margin=dict(l=50, r=50, t=60, b=60),
        height=480,
        barmode="group",
        bargap=0.15,
        bargroupgap=0.04,
        yaxis=dict(
            title=dict(text="<b>Volume de Notas</b>", font=dict(size=13, color="#000000")),
            showgrid=True,
            gridcolor="#e9ecef",
            range=[0, max_sb * 1.30],
        ),
        xaxis=dict(type="category", tickfont=dict(size=11, color="#000000")),
        legend=dict(orientation="h", y=1.14, x=1, xanchor="right", font=dict(size=12, color="#000000")),
    )

    st.plotly_chart(fig_sb, use_container_width=True)

    # =========================================================================
    # 2. RELAÇÃO DIÁRIA: NOTAS REALIZADAS VS. VOLUME EXPEDIDO
    # =========================================================================
    st.markdown("---")
    st.markdown("### 📊 Relação Diária: Notas Realizadas vs. Volume Expedido")

    y_notas = df_p["Notas_Realizadas"].fillna(0).astype(int).tolist()
    y_exp = df_p["Total_Expedidos"].fillna(0).astype(int).tolist()
    max_ne = max(max(y_notas, default=10), max(y_exp, default=10))

    fig_ne = go.Figure()

    fig_ne.add_trace(
        go.Bar(
            x=eixo_x,
            y=y_notas,
            name="Notas Realizadas (PVs)",
            marker=dict(color="#1f77b4", line=dict(color="#000000", width=0.8)),
            text=[str(v) if v > 0 else "" for v in y_notas],
            textposition="outside",
            textfont=dict(size=11, color="#000000", family="Arial Black"),
            cliponaxis=False,
            hovertemplate="<b>Data: %{x}</b><br>Notas Realizadas: %{y}<extra></extra>",
        )
    )

    fig_ne.add_trace(
        go.Bar(
            x=eixo_x,
            y=y_exp,
            name="Volume Expedido",
            marker=dict(color="#ff7f0e", line=dict(color="#000000", width=0.8)),
            text=[str(v) if v > 0 else "" for v in y_exp],
            textposition="outside",
            textfont=dict(size=11, color="#d97706", family="Arial Black"),
            cliponaxis=False,
            hovertemplate="<b>Data: %{x}</b><br>Volume Expedido: %{y}<extra></extra>",
        )
    )

    fig_ne.update_layout(
        template="plotly_white",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#000000", size=12, family="Arial"),
        margin=dict(l=50, r=50, t=60, b=60),
        height=480,
        barmode="group",
        bargap=0.15,
        bargroupgap=0.04,
        yaxis=dict(
            title=dict(text="<b>Volume de Pedidos / Notas</b>", font=dict(size=13, color="#000000")),
            showgrid=True,
            gridcolor="#e9ecef",
            range=[0, max_ne * 1.30],
        ),
        xaxis=dict(type="category", tickfont=dict(size=11, color="#000000")),
        legend=dict(orientation="h", y=1.14, x=1, xanchor="right", font=dict(size=12, color="#000000")),
    )

    st.plotly_chart(fig_ne, use_container_width=True)