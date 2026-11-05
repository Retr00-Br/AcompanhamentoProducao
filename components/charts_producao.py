import pandas as pd
import plotly.graph_objects as go
import streamlit as st


def render_graficos_producao(df_filtrado: pd.DataFrame, col_fat_ativa: str, unidade_selecionada: str):
    if df_filtrado is None or df_filtrado.empty:
        st.info("Sem registros de produção para o período selecionado.")
        return

    # 🔒 FILTRO DE CORTE: Considera a partir de 07/10/2026
    dt_corte = pd.to_datetime("2026-10-07")
    df_chart = df_filtrado[df_filtrado["DATA"] >= dt_corte].copy().sort_values("DATA").reset_index(drop=True)

    if df_chart.empty:
        st.info("Sem dados de Produção para o período selecionado (Lançamentos iniciam em 07/10).")
        return

    df_chart["Data_Str"] = df_chart["DATA"].dt.strftime("%d/%m")
    eixo_x = df_chart["Data_Str"].tolist()

    # -------------------------------------------------------------
    # GRÁFICO 1: Produção Diária Isolada: Notas Saudáveis vs. Backlog
    # -------------------------------------------------------------
    st.markdown("---")
    st.markdown("### 📋 Produção Diária Isolada: Notas Saudáveis vs. Backlog")

    y_saudavel = [int(v) for v in df_chart.get("Saudavel", pd.Series([0] * len(df_chart))).fillna(0)]
    y_backlog = [int(v) for v in df_chart.get("Backlog", pd.Series([0] * len(df_chart))).fillna(0)]

    max_val1 = max(max(y_saudavel, default=10), max(y_backlog, default=10))

    fig1 = go.Figure()

    fig1.add_trace(
        go.Bar(
            x=eixo_x,
            y=y_backlog,
            name="Backlog",
            marker=dict(color="#c0392b", line=dict(color="#000000", width=1.0)),
            text=[f"<b>{v}</b>" if v > 0 else "" for v in y_backlog],
            textfont=dict(color="#000000", size=11, family="Arial Black"),
            textposition="outside",
            cliponaxis=False,
            hovertemplate="<b>Data: %{x}</b><br>Backlog: %{y}<extra></extra>",
        )
    )

    fig1.add_trace(
        go.Bar(
            x=eixo_x,
            y=y_saudavel,
            name="Notas Saudáveis",
            marker=dict(color="#16a085", line=dict(color="#000000", width=1.0)),
            text=[f"<b>{v}</b>" if v > 0 else "" for v in y_saudavel],
            textfont=dict(color="#000000", size=11, family="Arial Black"),
            textposition="outside",
            cliponaxis=False,
            hovertemplate="<b>Data: %{x}</b><br>Saudável: %{y}<extra></extra>",
        )
    )

    fig1.update_layout(
        template="plotly_white",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#000000", size=12, family="Arial"),
        margin=dict(l=50, r=50, t=50, b=60),
        height=500,
        barmode="group",
        bargap=0.20,
        yaxis=dict(
            title=dict(text="<b>Quantidade de Pedidos (PV)</b>", font=dict(size=13, color="#000000")),
            showgrid=True,
            gridcolor="#e9ecef",
            range=[0, max_val1 * 1.35],
        ),
        xaxis=dict(type="category", tickfont=dict(size=11, color="#000000")),
        legend=dict(orientation="h", y=1.12, x=1, xanchor="right", font=dict(size=12, color="#000000")),
    )

    st.plotly_chart(fig1, use_container_width=True)

    # -------------------------------------------------------------
    # GRÁFICO 2: Relação Diária: Notas Realizadas vs. Volume Expedido (07/10 - Atual)
    # -------------------------------------------------------------
    st.markdown("---")
    st.markdown("### 📊 Relação Diária: Notas Realizadas vs. Volume Expedido (07/10 - Atual)")

    col_realizadas = "Notas_Realizadas" if "Notas_Realizadas" in df_chart.columns else "Total_PVs"
    col_expedicao = "Total_Expedidos" if "Total_Expedidos" in df_chart.columns else "Total_Expedicao"

    y_realizadas = [int(v) for v in df_chart.get(col_realizadas, pd.Series([0] * len(df_chart))).fillna(0)]
    y_expedicao = [int(v) for v in df_chart.get(col_expedicao, pd.Series([0] * len(df_chart))).fillna(0)]

    max_val2 = max(max(y_realizadas, default=10), max(y_expedicao, default=10))

    fig2 = go.Figure()

    fig2.add_trace(
        go.Bar(
            x=eixo_x,
            y=y_realizadas,
            name="Notas Realizadas (PVs)",
            marker=dict(color="#2980b9", line=dict(color="#000000", width=1.0)),
            text=[f"<b>{v}</b>" if v > 0 else "" for v in y_realizadas],
            textfont=dict(color="#000000", size=11, family="Arial Black"),
            textposition="outside",
            cliponaxis=False,
            hovertemplate="<b>Data: %{x}</b><br>Notas Realizadas: %{y}<extra></extra>",
        )
    )

    fig2.add_trace(
        go.Bar(
            x=eixo_x,
            y=y_expedicao,
            name="Volume Expedido",
            marker=dict(color="#e67e22", line=dict(color="#000000", width=1.0)),
            text=[f"<b>{v}</b>" if v > 0 else "" for v in y_expedicao],
            textfont=dict(color="#000000", size=11, family="Arial Black"),
            textposition="outside",
            cliponaxis=False,
            hovertemplate="<b>Data: %{x}</b><br>Expedição: %{y}<extra></extra>",
        )
    )

    fig2.update_layout(
        template="plotly_white",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#000000", size=12, family="Arial"),
        margin=dict(l=50, r=50, t=50, b=60),
        height=500,
        barmode="group",
        bargap=0.20,
        yaxis=dict(
            title=dict(text="<b>Volume de Pedidos / Notas</b>", font=dict(size=13, color="#000000")),
            showgrid=True,
            gridcolor="#e9ecef",
            range=[0, max_val2 * 1.35],
        ),
        xaxis=dict(type="category", tickfont=dict(size=11, color="#000000")),
        legend=dict(orientation="h", y=1.12, x=1, xanchor="right", font=dict(size=12, color="#000000")),
    )

    st.plotly_chart(fig2, use_container_width=True)