import pandas as pd
import plotly.graph_objects as go
import streamlit as st


def _fmt_brl(val: float) -> str:
    sinal = "-" if val < 0 else ""
    return f"{sinal}R$ {abs(val):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def render_secao_faturamento(
    df_filtrado: pd.DataFrame,
    unidade_selecionada: str = "Todas as Unidades (Geral)",
    df_diario_completo: pd.DataFrame = None,
):
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

    mask_ativos = (df_plot[col_fat] > 0) | (df_plot[col_dev].abs() > 0)
    if mask_ativos.any():
        df_plot = df_plot[mask_ativos].copy().reset_index(drop=True)

    y_fat = df_plot[col_fat].tolist()
    y_dev = df_plot[col_dev].abs().tolist()
    x_datas = df_plot["Data_Str"].tolist()

    max_y = max(max(y_fat, default=100.0), max(y_dev, default=100.0), 100.0)

    # =========================================================================
    # 1. GRÁFICO DIÁRIO: FATURAMENTO X DEVOLUÇÕES
    # =========================================================================
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
        height=500,
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

    # =========================================================================
    # 2. GRÁFICO MENSAL: VALOR TOTAL DE FATURAMENTO POR MÊS
    # =========================================================================
    df_base_mensal = df_diario_completo.copy() if (df_diario_completo is not None and not df_diario_completo.empty) else df_filtrado.copy()
    df_base_mensal["DATA"] = pd.to_datetime(df_base_mensal["DATA"], errors="coerce").dt.normalize()
    df_base_mensal = df_base_mensal.dropna(subset=["DATA"]).copy()
    df_base_mensal["Mes_Ano"] = df_base_mensal["DATA"].dt.strftime("%Y-%m")

    col_fat_m = col_fat if col_fat in df_base_mensal.columns else "Todas as Unidades (Geral)_Fat"
    col_dev_m = col_dev if col_dev in df_base_mensal.columns else "Todas as Unidades (Geral)_Dev"

    agg_dict = {col_fat_m: "sum", col_dev_m: "sum"}
    if "Todas as Unidades (Geral)_Liq" in df_base_mensal.columns and unidade_selecionada == "Todas as Unidades (Geral)":
        agg_dict["Todas as Unidades (Geral)_Liq"] = "sum"

    df_mensal_tot = (
        df_base_mensal.groupby("Mes_Ano", as_index=False)
        .agg(agg_dict)
        .sort_values("Mes_Ano")
        .reset_index(drop=True)
    )
    df_mensal_tot = df_mensal_tot[(df_mensal_tot[col_fat_m] > 0) | (df_mensal_tot[col_dev_m].abs() > 0)].reset_index(drop=True)

    if not df_mensal_tot.empty:
        st.markdown("---")
        st.markdown(f"### 📅 Valor Total de Faturamento por Mês — {unidade_selecionada}")

        if "Todas as Unidades (Geral)_Liq" in df_mensal_tot.columns and unidade_selecionada == "Todas as Unidades (Geral)":
            y_m_bruto = df_mensal_tot[col_fat_m].tolist()
            y_m_liq = df_mensal_tot["Todas as Unidades (Geral)_Liq"].tolist()
        else:
            y_m_bruto = df_mensal_tot[col_fat_m].tolist()
            y_m_liq = (df_mensal_tot[col_fat_m] - df_mensal_tot[col_dev_m].abs()).tolist()

        y_m_dev = df_mensal_tot[col_dev_m].abs().tolist()
        x_m = df_mensal_tot["Mes_Ano"].tolist()
        max_m = max(max(y_m_bruto, default=100.0), max(y_m_liq, default=100.0), 100.0)

        fig_mensal = go.Figure()
        fig_mensal.add_trace(
            go.Bar(
                x=x_m,
                y=y_m_bruto,
                name="Faturamento Bruto (R$)",
                marker=dict(color="#1f77b4", line=dict(color="#000000", width=0.8)),
                text=[_fmt_brl(v) if v > 0 else "" for v in y_m_bruto],
                textposition="outside",
                textfont=dict(size=10, color="#000000", family="Arial Black"),
                cliponaxis=False,
                hovertemplate="<b>Mês: %{x}</b><br>Faturamento Bruto: R$ %{y:,.2f}<extra></extra>",
            )
        )
        fig_mensal.add_trace(
            go.Bar(
                x=x_m,
                y=y_m_liq,
                name="Faturamento Líquido (R$)",
                marker=dict(color="#16a34a", line=dict(color="#000000", width=0.8)),
                text=[_fmt_brl(v) if v > 0 else "" for v in y_m_liq],
                textposition="outside",
                textfont=dict(size=10, color="#16a34a", family="Arial Black"),
                cliponaxis=False,
                hovertemplate="<b>Mês: %{x}</b><br>Faturamento Líquido: R$ %{y:,.2f}<extra></extra>",
            )
        )
        fig_mensal.add_trace(
            go.Bar(
                x=x_m,
                y=y_m_dev,
                name="Devoluções (R$)",
                marker=dict(color="#d62728", line=dict(color="#000000", width=0.8)),
                text=[_fmt_brl(v) if v > 0 else "" for v in y_m_dev],
                textposition="outside",
                textfont=dict(size=10, color="#d62728", family="Arial Black"),
                cliponaxis=False,
                hovertemplate="<b>Mês: %{x}</b><br>Devoluções: R$ %{y:,.2f}<extra></extra>",
            )
        )

        fig_mensal.update_layout(
            template="plotly_white",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#000000", size=12, family="Arial"),
            height=480,
            margin=dict(l=50, r=40, t=55, b=50),
            barmode="group",
            bargap=0.22,
            yaxis=dict(
                title=dict(text="<b>Total Mensal (R$)</b>", font=dict(size=13, color="#000000")),
                showgrid=True,
                gridcolor="#e9ecef",
                range=[0, max_m * 1.26],
            ),
            xaxis=dict(type="category", tickfont=dict(size=11, color="#000000")),
            legend=dict(orientation="h", y=1.12, x=1.0, xanchor="right", font=dict(size=12, color="#000000")),
        )
        st.plotly_chart(fig_mensal, use_container_width=True)

    # =========================================================================
    # 3. GRÁFICO MENSAL COMPARATIVO: MATRIZ VS. FILIAIS
    # =========================================================================
    filiais_cols = {
        "0101 - Matriz": ("0101 - Matriz_Fat", "#1f77b4"),
        "0102 - Filial RJ": ("0102 - Filial RJ_Fat", "#ff7f0e"),
        "0103 - Filial CP": ("0103 - Filial CP_Fat", "#2ca02c"),
        "0104 - Filial SBC": ("0104 - Filial SBC_Fat", "#9467bd"),
    }
    cols_exist = [c for c, _ in filiais_cols.values() if c in df_base_mensal.columns]

    if cols_exist:
        df_comp_fil = (
            df_base_mensal.groupby("Mes_Ano", as_index=False)[cols_exist]
            .sum()
            .sort_values("Mes_Ano")
            .reset_index(drop=True)
        )
        df_comp_fil = df_comp_fil[df_comp_fil[cols_exist].sum(axis=1) > 0].reset_index(drop=True)

        if not df_comp_fil.empty:
            st.markdown("---")
            st.markdown("### 🏢 Comparativo Mensal de Faturamento: Matriz vs. Filiais")

            fig_fil = go.Figure()
            max_fil = 100.0
            for label_f, (col_f, cor_f) in filiais_cols.items():
                if col_f in df_comp_fil.columns:
                    vals_f = df_comp_fil[col_f].tolist()
                    max_fil = max(max_fil, max(vals_f, default=0.0))
                    fig_fil.add_trace(
                        go.Bar(
                            x=df_comp_fil["Mes_Ano"],
                            y=vals_f,
                            name=label_f,
                            marker=dict(color=cor_f, line=dict(color="#000000", width=0.8)),
                            text=[_fmt_brl(v) if v > 0 else "" for v in vals_f],
                            textposition="outside",
                            textfont=dict(size=9, color="#000000", family="Arial Black"),
                            cliponaxis=False,
                            hovertemplate=f"<b>%{{x}} — {label_f}</b><br>Faturamento: R$ %{{y:,.2f}}<extra></extra>",
                        )
                    )

            fig_fil.update_layout(
                template="plotly_white",
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#000000", size=12, family="Arial"),
                height=500,
                margin=dict(l=50, r=40, t=55, b=50),
                barmode="group",
                bargap=0.20,
                yaxis=dict(
                    title=dict(text="<b>Faturamento por Unidade (R$)</b>", font=dict(size=13, color="#000000")),
                    showgrid=True,
                    gridcolor="#e9ecef",
                    range=[0, max_fil * 1.28],
                ),
                xaxis=dict(type="category", tickfont=dict(size=11, color="#000000")),
                legend=dict(orientation="h", y=1.12, x=1.0, xanchor="right", font=dict(size=12, color="#000000")),
            )
            st.plotly_chart(fig_fil, use_container_width=True)