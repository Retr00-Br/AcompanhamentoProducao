import pandas as pd
import plotly.graph_objects as go
import streamlit as st


def render_secao_faturamento(df_filtrado: pd.DataFrame, unidade_selecionada: str):
    st.markdown("---")
    st.markdown(f"### 📈 Faturamento Diário x Devoluções — {unidade_selecionada}")

    if df_filtrado is None or df_filtrado.empty:
        st.info("Sem dados de faturamento para o período selecionado.")
        return

    col_fat = f"{unidade_selecionada}_Fat"
    col_dev = f"{unidade_selecionada}_Dev"

    if col_fat not in df_filtrado.columns:
        col_fat = "Todas as Unidades (Geral)_Fat"
    if col_dev not in df_filtrado.columns:
        col_dev = "Todas as Unidades (Geral)_Dev"

    df_chart = df_filtrado.copy().sort_values("DATA").reset_index(drop=True)
    df_chart["Data_Str"] = df_chart["DATA"].dt.strftime("%d/%m")
    eixo_x = df_chart["Data_Str"].tolist()

    y_fat = df_chart[col_fat].fillna(0.0).tolist()
    y_dev = df_chart[col_dev].fillna(0.0).tolist()

    # Formatação completa sem arredondamentos em k/M (Ex: R$ 845.230,50)
    def fmt_val_completo(v):
        if v > 0:
            return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return ""

    labels_fat = [fmt_val_completo(v) for v in y_fat]
    labels_dev = [fmt_val_completo(v) for v in y_dev]

    max_val = max(max(y_fat, default=100), max(y_dev, default=100))

    fig = go.Figure()

    # 1. Coluna de Faturamento (Azul) - Com valor numérico completo
    fig.add_trace(
        go.Bar(
            x=eixo_x,
            y=y_fat,
            name="Faturamento (R$)",
            marker=dict(color="#1f77b4", line=dict(color="#000000", width=0.8)),
            text=labels_fat,
            textposition="outside",
            textfont=dict(size=10, color="#000000", family="Arial Black"),
            cliponaxis=False,
            hovertemplate="<b>Data: %{x}</b><br>Faturamento: R$ %{y:,.2f}<extra></extra>",
        )
    )

    # 2. Coluna de Devoluções (Vermelha) - Com valor numérico completo
    fig.add_trace(
        go.Bar(
            x=eixo_x,
            y=y_dev,
            name="Devoluções (R$)",
            marker=dict(color="#d62728", line=dict(color="#000000", width=0.8)),
            text=labels_dev,
            textposition="outside",
            textfont=dict(size=10, color="#d62728", family="Arial Black"),
            cliponaxis=False,
            hovertemplate="<b>Data: %{x}</b><br>Devolução: R$ %{y:,.2f}<extra></extra>",
        )
    )

    fig.update_layout(
        template="plotly_white",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#000000", size=12, family="Arial"),
        margin=dict(l=50, r=50, t=60, b=60),
        height=540,
        barmode="group",
        bargap=0.12,
        bargroupgap=0.04,
        yaxis=dict(
            title=dict(text="<b>Faturamento Monetário (R$)</b>", font=dict(size=13, color="#000000")),
            showgrid=True,
            gridcolor="#e9ecef",
            range=[0, max_val * 1.35],
        ),
        xaxis=dict(type="category", tickfont=dict(size=11, color="#000000")),
        legend=dict(orientation="h", y=1.14, x=1, xanchor="right", font=dict(size=12, color="#000000")),
    )

    st.plotly_chart(fig, use_container_width=True)