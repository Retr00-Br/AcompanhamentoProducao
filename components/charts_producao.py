import pandas as pd
import plotly.graph_objects as go
import streamlit as st


def render_graficos_producao(df_filtrado: pd.DataFrame, col_fat_ativa: str, unidade_selecionada: str):
    if df_filtrado is None or df_filtrado.empty:
        st.info("Sem dados de produção e expedição para o período selecionado.")
        return

    df_p = df_filtrado.copy()
    df_p["DATA"] = pd.to_datetime(df_p["DATA"]).dt.normalize()

    # =========================================================================
    # CORREÇÃO DE BUG: Ignora o período de faturamento de agosto/setembro sem produção.
    # Inicia estritamente a partir da primeira data com dados reais de Produção/Expedição (07/10) até a data atual.
    # =========================================================================
    mask_dados_prod = (
        (df_p.get("Notas_Realizadas", 0) > 0)
        | (df_p.get("Saudavel", 0) > 0)
        | (df_p.get("Backlog", 0) > 0)
        | (df_p.get("Total_Expedidos", 0) > 0)
    )

    if mask_dados_prod.any():
        data_inicio_real = df_p.loc[mask_dados_prod, "DATA"].min()
        data_fim_real = df_p.loc[mask_dados_prod, "DATA"].max()
        df_p = df_p[(df_p["DATA"] >= data_inicio_real) & (df_p["DATA"] <= data_fim_real)].copy().reset_index(drop=True)
    else:
        st.info("Sem registros de produção ou expedição no intervalo selecionado.")
        return

    df_p["Data_Str"] = df_p["DATA"].dt.strftime("%d/%m")

    # =========================================================================
    # 1. PRODUÇÃO DIÁRIA ISOLADA: NOTAS SAUDÁVEIS VS. BACKLOG
    # =========================================================================
    st.markdown("---")
    st.markdown("### 🏭 Produção Diária Isolada: Notas Saudáveis vs. Backlog")

    fig_sb = go.Figure()

    fig_sb.add_trace(
        go.Bar(
            x=df_p["Data_Str"],
            y=df_p["Saudavel"],
            name="Notas Saudáveis",
            marker=dict(color="#2ca02c", line=dict(color="#000000", width=0.8)),
            text=[str(int(v)) if v > 0 else "" for v in df_p["Saudavel"]],
            textposition="outside",
            textfont=dict(size=10, color="#000000", family="Arial Black"),
            cliponaxis=False,
            hovertemplate="<b>Data: %{x}</b><br>Notas Saudáveis: %{y}<extra></extra>",
        )
    )

    fig_sb.add_trace(
        go.Bar(
            x=df_p["Data_Str"],
            y=df_p["Backlog"],
            name="Backlog",
            marker=dict(color="#d62728", line=dict(color="#000000", width=0.8)),
            text=[str(int(v)) if v > 0 else "" for v in df_p["Backlog"]],
            textposition="outside",
            textfont=dict(size=10, color="#d62728", family="Arial Black"),
            cliponaxis=False,
            hovertemplate="<b>Data: %{x}</b><br>Backlog: %{y}<extra></extra>",
        )
    )

    max_sb = max(df_p["Saudavel"].max(), df_p["Backlog"].max(), 10)

    fig_sb.update_layout(
        template="plotly_white",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#000000", size=12, family="Arial"),
        margin=dict(l=50, r=30, t=50, b=60),
        height=480,
        barmode="group",
        bargap=0.20,
        yaxis=dict(
            title=dict(text="<b>Volume de Notas</b>", font=dict(size=13, color="#000000")),
            showgrid=True,
            gridcolor="#e9ecef",
            range=[0, max_sb * 1.25],
        ),
        xaxis=dict(type="category", tickangle=-45, tickfont=dict(size=11, color="#000000")),
        legend=dict(orientation="h", y=1.12, x=1, xanchor="right", font=dict(size=12, color="#000000")),
    )

    st.plotly_chart(fig_sb, use_container_width=True)

    # =========================================================================
    # 2. RELAÇÃO DIÁRIA: NOTAS REALIZADAS VS. VOLUME EXPEDIDO
    # =========================================================================
    st.markdown("---")
    st.markdown("### 📊 Relação Diária: Notas Realizadas vs. Volume Expedido")

    fig_exp = go.Figure()

    fig_exp.add_trace(
        go.Bar(
            x=df_p["Data_Str"],
            y=df_p["Notas_Realizadas"],
            name="Notas Realizadas (PVs)",
            marker=dict(color="#1f77b4", line=dict(color="#000000", width=0.8)),
            text=[str(int(v)) if v > 0 else "" for v in df_p["Notas_Realizadas"]],
            textposition="outside",
            textfont=dict(size=10, color="#000000", family="Arial Black"),
            cliponaxis=False,
            hovertemplate="<b>Data: %{x}</b><br>Notas Realizadas: %{y}<extra></extra>",
        )
    )

    fig_exp.add_trace(
        go.Bar(
            x=df_p["Data_Str"],
            y=df_p["Total_Expedidos"],
            name="Volume Expedido",
            marker=dict(color="#ff7f0e", line=dict(color="#000000", width=0.8)),
            text=[str(int(v)) if v > 0 else "" for v in df_p["Total_Expedidos"]],
            textposition="outside",
            textfont=dict(size=10, color="#000000", family="Arial Black"),
            cliponaxis=False,
            hovertemplate="<b>Data: %{x}</b><br>Volume Expedido: %{y}<extra></extra>",
        )
    )

    max_exp = max(df_p["Notas_Realizadas"].max(), df_p["Total_Expedidos"].max(), 10)

    fig_exp.update_layout(
        template="plotly_white",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#000000", size=12, family="Arial"),
        margin=dict(l=50, r=30, t=50, b=60),
        height=480,
        barmode="group",
        bargap=0.20,
        yaxis=dict(
            title=dict(text="<b>Volume de Pedidos / Notas</b>", font=dict(size=13, color="#000000")),
            showgrid=True,
            gridcolor="#e9ecef",
            range=[0, max_exp * 1.25],
        ),
        xaxis=dict(type="category", tickangle=-45, tickfont=dict(size=11, color="#000000")),
        legend=dict(orientation="h", y=1.12, x=1, xanchor="right", font=dict(size=12, color="#000000")),
    )

    st.plotly_chart(fig_exp, use_container_width=True)