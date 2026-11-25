import pandas as pd
import plotly.graph_objects as go
import streamlit as st


def render_graficos_producao(
    df_filtrado: pd.DataFrame,
    col_fat_ativa: str,
    unidade_selecionada: str,
    df_exp_detalhado: pd.DataFrame = None,
    filial_sel: str = "Todas as Filiais",
    cliente_sel: str = "Todos os Clientes",
):
    if df_filtrado is None or df_filtrado.empty:
        st.info("Sem dados de produção e expedição para o período selecionado.")
        return

    df_p = df_filtrado.copy()
    df_p["DATA"] = pd.to_datetime(df_p["DATA"]).dt.normalize()

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
    filtro_ativo = (filial_sel != "Todas as Filiais") or (cliente_sel != "Todos os Clientes")

    # =========================================================================
    # 1. PRODUÇÃO DIÁRIA ISOLADA: NOTAS SAUDÁVEIS VS. BACKLOG
    # =========================================================================
    st.markdown("---")
    st.markdown("### 🏭 Produção Diária Isolada: Notas Saudáveis vs. Backlog")
    if filtro_ativo:
        st.caption(
            "ℹ️ *Os indicadores de Produção (Saudável x Backlog) refletem o volume global do galpão; "
            "os filtros de Filial e Cliente aplicam-se diretamente aos gráficos e tabelas de Expedição abaixo.*"
        )

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
    subtitulo_filtro = f" — {filial_sel} | {cliente_sel}" if filtro_ativo else ""
    st.markdown(f"### 📊 Relação Diária: Notas Realizadas vs. Volume Expedido{subtitulo_filtro}")

    fig_exp = go.Figure()

    if not filtro_ativo:
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
            name="Volume Expedido (NFs)",
            marker=dict(color="#ff7f0e", line=dict(color="#000000", width=0.8)),
            text=[str(int(v)) if v > 0 else "" for v in df_p["Total_Expedidos"]],
            textposition="outside",
            textfont=dict(size=10, color="#000000", family="Arial Black"),
            cliponaxis=False,
            hovertemplate="<b>Data: %{x}</b><br>Volume Expedido: %{y}<extra></extra>",
        )
    )

    max_exp = max(
        (df_p["Notas_Realizadas"].max() if not filtro_ativo else 0),
        df_p["Total_Expedidos"].max(),
        10,
    )

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

    # =========================================================================
    # 3. DETALHAMENTO EXPEDIÇÃO GERAL (TOP 10 CLIENTES & ROMANEIOS)
    # =========================================================================
    if df_exp_detalhado is not None and not df_exp_detalhado.empty:
        st.markdown("---")
        st.markdown("### 🚚 Detalhamento da Expedição Geral (Por Cliente, Filial & NF)")

        col_g1, col_g2 = st.columns([1.25, 1.15])

        with col_g1:
            st.markdown("#### 🏆 Top 10 Clientes por Volume de NFs Expedidas")
            df_top_cli = (
                df_exp_detalhado.groupby(["Cliente", "Filial_Nome"], as_index=False)["Num.NF"]
                .count()
                .rename(columns={"Num.NF": "Qtd_NFs"})
                .sort_values("Qtd_NFs", ascending=False)
                .head(10)
                .reset_index(drop=True)
            )
            df_top_cli["Label"] = df_top_cli["Cliente"] + " (" + df_top_cli["Filial_Nome"].str[:4] + ")"

            fig_top = go.Figure(
                go.Bar(
                    y=df_top_cli["Label"],
                    x=df_top_cli["Qtd_NFs"],
                    orientation="h",
                    marker=dict(color="#1f77b4", line=dict(color="#000000", width=0.8)),
                    text=df_top_cli["Qtd_NFs"],
                    textposition="outside",
                    textfont=dict(size=10, color="#000000", family="Arial Black"),
                    cliponaxis=False,
                    hovertemplate="<b>%{y}</b><br>NFs Expedidas: %{x}<extra></extra>",
                )
            )
            max_top = max(df_top_cli["Qtd_NFs"].max() if not df_top_cli.empty else 10, 10)
            fig_top.update_layout(
                template="plotly_white",
                height=430,
                margin=dict(l=160, r=45, t=30, b=30),
                xaxis=dict(title="<b>Qtd. Notas Fiscais Expedidas</b>", range=[0, max_top * 1.22], gridcolor="#e9ecef"),
                yaxis=dict(autorange="reversed", tickfont=dict(size=10, color="#000000")),
            )
            st.plotly_chart(fig_top, use_container_width=True)

        with col_g2:
            st.markdown("#### 📋 Notas Fiscais & Romaneios Expedidos")
            df_tab_exp = df_exp_detalhado.copy()
            df_tab_exp["Dt. Romaneio"] = df_tab_exp["DATA"].dt.strftime("%d/%m/%Y")
            st.dataframe(
                df_tab_exp[["Dt. Romaneio", "Filial_Nome", "Cliente", "Num.PV", "Num.NF"]].rename(
                    columns={
                        "Filial_Nome": "Filial",
                        "Cliente": "Cliente (Nome Fantasia)",
                        "Num.PV": "Pedido (PV)",
                        "Num.NF": "Nota Fiscal",
                    }
                ),
                use_container_width=True,
                height=430,
                hide_index=True,
            )