import pandas as pd
import plotly.graph_objects as go
import streamlit as st


def _fmt_brl(val: float) -> str:
    return f"R$ {abs(val):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def render_secao_faturamento(df_filtrado: pd.DataFrame, unidade_selecionada: str = "Todas as Unidades (Geral)"):
    if df_filtrado is None or df_filtrado.empty:
        st.info("Sem dados de faturamento para o período selecionado.")
        return

    col_fat = f"{unidade_selecionada}_Fat"
    col_dev = f"{unidade_selecionada}_Dev"

    if col_fat not in df_filtrado.columns:
        col_fat = "Todas as Unidades (Geral)_Fat"
    if col_dev not in df_filtrado.columns:
        col_dev = "Todas as Unidades (Geral)_Dev"

    df_plot = df_filtrado.copy()
    if "Data_Str" not in df_plot.columns:
        df_plot["Data_Str"] = pd.to_datetime(df_plot["DATA"]).dt.strftime("%d/%m")

    # Filtra dias em que houve faturamento ou devolução (evita barras zeradas vazias no fim)
    mask_ativos = (df_plot[col_fat] > 0) | (df_plot[col_dev].abs() > 0)
    if mask_ativos.any():
        df_plot = df_plot[mask_ativos].copy().reset_index(drop=True)

    y_fat = df_plot[col_fat].tolist()
    y_dev = df_plot[col_dev].abs().tolist()  # Módulo positivo para exibir a barra acima do eixo 0
    x_datas = df_plot["Data_Str"].tolist()

    max_y = max(max(y_fat, default=100.0), max(y_dev, default=100.0), 100.0)

    st.markdown(f"### 📈 Faturamento Diário x Devoluções — {unidade_selecionada}")

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=x_datas,
            y=y_fat,
            name="Faturamento (R$)",
            marker=dict(color="#1f77b4", line=dict(color="#000000", width=0.8)),
            text=[_fmt_brl(v) if v > 0 else "" for v in y_fat],
            textposition="outside",
            textfont=dict(size=9, color="#000000", family="Arial Black"),
            cliponaxis=False,
            hovertemplate="<b>Data: %{x}</b><br>Faturamento: R$ %{y:,.2f}<extra></extra>",
        )
    )

    fig.add_trace(
        go.Bar(
            x=x_datas,
            y=y_dev,
            name="Devoluções (R$)",
            marker=dict(color="#d62728", line=dict(color="#000000", width=0.8)),
            text=[_fmt_brl(v) if v > 0 else "" for v in y_dev],
            textposition="outside",
            textfont=dict(size=9, color="#d62728", family="Arial Black"),
            cliponaxis=False,
            hovertemplate="<b>Data: %{x}</b><br>Devoluções: R$ %{y:,.2f}<extra></extra>",
        )
    )

    fig.update_layout(
        template="plotly_white",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#000000", size=12, family="Arial"),
        height=520,
        margin=dict(l=50, r=40, t=55, b=50),
        barmode="group",
        bargap=0.22,
        bargroupgap=0.05,
        yaxis=dict(
            title=dict(text="<b>Faturamento Monetário (R$)</b>", font=dict(size=13, color="#000000")),
            showgrid=True,
            gridcolor="#e9ecef",
            range=[0, max_y * 1.25],
        ),
        xaxis=dict(
            type="category",
            tickfont=dict(size=11, color="#000000"),
            showgrid=False,
        ),
        legend=dict(
            orientation="h",
            y=1.12,
            x=1.0,
            xanchor="right",
            font=dict(size=12, color="#000000"),
        ),
    )

    st.plotly_chart(fig, use_container_width=True)