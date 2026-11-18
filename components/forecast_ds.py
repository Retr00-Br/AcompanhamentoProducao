import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st


def _fmt_brl(val: float) -> str:
    sinal = "-" if val < 0 else ""
    return f"{sinal}R$ {abs(val):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _fmt_brl_compacto(val: float) -> str:
    abs_v = abs(val)
    if abs_v >= 1_000_000:
        return f"R$ {val / 1_000_000:,.2f}M".replace(".", ",")
    if abs_v >= 1_000:
        return f"R$ {val / 1_000:,.1f}k".replace(".", ",")
    return _fmt_brl(val)


def _fmt_int(val: float) -> str:
    return f"{int(round(val)):,}".replace(",", ".")


def _gerar_proximos_dias_uteis(ultima_data: pd.Timestamp, n_dias: int) -> pd.DatetimeIndex:
    """Gera os próximos N dias operacionais (segunda a sábado, excluindo domingos)."""
    datas = []
    curr = pd.Timestamp(ultima_data) + pd.Timedelta(days=1)
    while len(datas) < n_dias:
        if curr.weekday() != 6:
            datas.append(curr)
        curr += pd.Timedelta(days=1)
    return pd.DatetimeIndex(datas)


def _ajustar_e_prever_serie(
    datas_hist: pd.DatetimeIndex,
    valores_hist: np.ndarray,
    datas_fut: pd.DatetimeIndex,
    modelo_escolhido: str,
) -> dict:
    """
    Ajusta modelos de Data Science (OLS, Ridge Sazonal, Polinomial Amortecido, Holt Linear e Ensemble)
    retornando histórico ajustado, previsão futura, intervalo de confiança 95% e métricas de erro.
    """
    y = np.asarray(valores_hist, dtype=float)
    n = len(y)
    h = len(datas_fut)

    if n < 3:
        media_const = float(np.mean(y)) if n > 0 else 0.0
        fut_const = np.full(h, max(media_const, 0.0))
        return {
            "hist_fit": np.full(n, max(media_const, 0.0)),
            "forecast": fut_const,
            "upper_95": fut_const * 1.15,
            "lower_95": np.maximum(fut_const * 0.85, 0.0),
            "rmse": 0.0,
            "r2": 0.0,
            "slope_dia": 0.0,
            "modelos_detalhe": {
                "Ensemble Ponderado (Média DS)": fut_const,
                "Regressão Linear (OLS)": fut_const,
                "Ridge + Sazonalidade Semanal": fut_const,
                "Polinomial Grau 2 (Amortecido)": fut_const,
                "Suavização Exponencial (Holt)": fut_const,
            },
        }

    t = np.arange(n, dtype=float)
    t_fut = np.arange(n, n + h, dtype=float)

    # 1. Regressão Linear Simples (OLS)
    b_ols, a_ols = np.polyfit(t, y, 1)
    fit_ols = a_ols + b_ols * t
    pred_ols = np.maximum(a_ols + b_ols * t_fut, 0.0)

    # 2. Regressão Ridge (L2) + Sazonalidade por Dia da Semana
    dows_all = list(range(6))
    t_scale = max(float(n), 1.0)

    def _build_design_matrix(idx_t: np.ndarray, dts: pd.DatetimeIndex) -> np.ndarray:
        cols = [np.ones(len(idx_t)), idx_t / t_scale]
        for d in dows_all[1:]:
            cols.append((dts.dayofweek == d).astype(float))
        return np.column_stack(cols)

    X_hist = _build_design_matrix(t, datas_hist)
    X_fut = _build_design_matrix(t_fut, datas_fut)

    lam = 1.5
    reg = np.eye(X_hist.shape[1]) * lam
    reg[0, 0] = 0.0
    beta_ridge = np.linalg.solve(X_hist.T @ X_hist + reg, X_hist.T @ y)

    fit_ridge = X_hist @ beta_ridge
    pred_ridge = np.maximum(X_fut @ beta_ridge, 0.0)

    # 3. Regressão Polinomial Grau 2 (Amortecida)
    if n >= 6:
        c2, c1, c0 = np.polyfit(t, y, 2)
        fit_poly = c2 * (t**2) + c1 * t + c0
        t_fut_damp = n + np.cumsum(0.96 ** np.arange(1, h + 1))
        pred_poly = np.maximum(c2 * (t_fut_damp**2) + c1 * t_fut_damp + c0, 0.0)
    else:
        fit_poly = fit_ols.copy()
        pred_poly = pred_ols.copy()

    # 4. Suavização Exponencial Dupla (Holt Linear)
    alpha, beta_h, phi = 0.35, 0.12, 0.92
    level = y[0]
    trend = (y[1] - y[0]) if n > 1 else 0.0
    fit_holt = np.zeros(n)
    fit_holt[0] = level
    for i in range(1, n):
        prev_level = level
        level = alpha * y[i] + (1 - alpha) * (level + phi * trend)
        trend = beta_h * (level - prev_level) + (1 - beta_h) * phi * trend
        fit_holt[i] = prev_level + phi * trend

    pred_holt = np.zeros(h)
    for step in range(1, h + 1):
        phi_sum = sum(phi**k for k in range(1, step + 1))
        pred_holt[step - 1] = max(level + phi_sum * trend, 0.0)

    # 5. Ensemble Ponderado (Média Inteligente DS)
    fit_ens = 0.30 * fit_ols + 0.35 * fit_ridge + 0.15 * fit_poly + 0.20 * fit_holt
    pred_ens = np.maximum(
        0.30 * pred_ols + 0.35 * pred_ridge + 0.15 * pred_poly + 0.20 * pred_holt,
        0.0,
    )

    mapa_modelos = {
        "Ensemble Ponderado (Média DS)": (fit_ens, pred_ens),
        "Regressão Linear (OLS)": (fit_ols, pred_ols),
        "Ridge + Sazonalidade Semanal": (fit_ridge, pred_ridge),
        "Polinomial Grau 2 (Amortecido)": (fit_poly, pred_poly),
        "Suavização Exponencial (Holt)": (fit_holt, pred_holt),
    }

    fit_sel, pred_sel = mapa_modelos.get(modelo_escolhido, (fit_ens, pred_ens))

    residuos = y - fit_sel
    rmse = float(np.sqrt(np.mean(residuos**2)))
    ss_res = float(np.sum(residuos**2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = max(0.0, 1.0 - (ss_res / ss_tot)) if ss_tot > 0 else 0.0

    fator_horizonte = np.sqrt(1.0 + (np.arange(1, h + 1) / max(n, 1)))
    margem_95 = 1.96 * rmse * fator_horizonte * 0.55

    upper_95 = np.maximum(pred_sel + margem_95, pred_sel)
    lower_95 = np.maximum(pred_sel - margem_95, 0.0)

    return {
        "hist_fit": np.maximum(fit_sel, 0.0),
        "forecast": pred_sel,
        "upper_95": upper_95,
        "lower_95": lower_95,
        "rmse": rmse,
        "r2": r2,
        "slope_dia": float(b_ols),
        "modelos_detalhe": {k: v[1] for k, v in mapa_modelos.items()},
    }


def _plot_serie_previsao(
    titulo: str,
    datas_hist: pd.DatetimeIndex,
    valores_hist: np.ndarray,
    res_modelo: dict,
    datas_fut: pd.DatetimeIndex,
    cor_hist: str = "#1f77b4",
    cor_prev: str = "#d97706",
    is_moeda: bool = True,
    janela_hist: int = 35,
):
    # Título renderizado fora do SVG para nunca sobrepor a legenda
    st.markdown(f"#### {titulo}")

    # Recorta a janela visual do histórico (mantendo todo o histórico no treino do modelo)
    if janela_hist > 0 and len(datas_hist) > janela_hist:
        datas_hist_vis = datas_hist[-janela_hist:]
        valores_hist_vis = valores_hist[-janela_hist:]
        fit_hist_vis = res_modelo["hist_fit"][-janela_hist:]
    else:
        datas_hist_vis = datas_hist
        valores_hist_vis = valores_hist
        fit_hist_vis = res_modelo["hist_fit"]

    fig = go.Figure()

    # Ordem estritamente cronológica: Passado (Esquerda) -> Futuro (Direita)
    x_hist_str = datas_hist_vis.strftime("%d/%m/%y").tolist()
    x_fut_str = datas_fut.strftime("%d/%m/%y").tolist()
    eixo_x_cronologico = x_hist_str + x_fut_str

    fmt_hover = "R$ %{y:,.2f}" if is_moeda else "%{y:,.1f}"

    # 1. Histórico Real
    fig.add_trace(
        go.Scatter(
            x=x_hist_str,
            y=valores_hist_vis,
            mode="lines+markers",
            name="Histórico Real",
            line=dict(color=cor_hist, width=2.4),
            marker=dict(size=6),
            hovertemplate=f"<b>Data: %{{x}}</b><br>Real: {fmt_hover}<extra></extra>",
        )
    )

    # 2. Linha de Tendência Ajustada
    fig.add_trace(
        go.Scatter(
            x=x_hist_str,
            y=fit_hist_vis,
            mode="lines",
            name="Tendência (Modelo)",
            line=dict(color="#64748b", width=1.8, dash="dot"),
            hovertemplate=f"<b>Data: %{{x}}</b><br>Ajuste Modelo: {fmt_hover}<extra></extra>",
        )
    )

    # 3. Intervalo de Confiança 95%
    fig.add_trace(
        go.Scatter(
            x=x_fut_str + x_fut_str[::-1],
            y=list(res_modelo["upper_95"]) + list(res_modelo["lower_95"][::-1]),
            fill="toself",
            fillcolor="rgba(217, 119, 6, 0.14)",
            line=dict(color="rgba(255,255,255,0)"),
            hoverinfo="skip",
            showlegend=True,
            name="IC 95%",
        )
    )

    # 4. Previsão Futura conectada ao último ponto real (sem voltar para trás!)
    x_conn = [x_hist_str[-1]] + x_fut_str
    y_conn = [float(valores_hist_vis[-1])] + list(res_modelo["forecast"])

    n_fut = len(x_fut_str)
    indices_rotulo = {0, n_fut // 2, n_fut - 1} if n_fut >= 4 else set(range(n_fut))
    textos_prev = [""]
    for i, v in enumerate(res_modelo["forecast"]):
        if i in indices_rotulo:
            textos_prev.append(_fmt_brl_compacto(v) if is_moeda else _fmt_int(v))
        else:
            textos_prev.append("")

    fig.add_trace(
        go.Scatter(
            x=x_conn,
            y=y_conn,
            mode="lines+markers+text",
            name="Previsão Futura",
            line=dict(color=cor_prev, width=3.0, dash="dash"),
            marker=dict(size=7, symbol="diamond"),
            text=textos_prev,
            textposition="top center",
            textfont=dict(size=10, color=cor_prev, family="Arial Black"),
            cliponaxis=False,
            hovertemplate=f"<b>Previsão: %{{x}}</b><br>Projetado: {fmt_hover}<extra></extra>",
        )
    )

    # Divisória vertical clara separando Histórico Real vs. Previsão Futura
    idx_div = len(x_hist_str) - 0.5
    fig.add_vline(
        x=idx_div,
        line_width=1.8,
        line_dash="dash",
        line_color="#475569",
    )
    fig.add_annotation(
        x=idx_div,
        y=1.02,
        yref="paper",
        text="<b>Início Previsão →</b>",
        showarrow=False,
        xanchor="left",
        font=dict(size=10, color="#475569"),
    )

    max_y = max(
        float(np.max(valores_hist_vis)) if len(valores_hist_vis) > 0 else 10.0,
        float(np.max(res_modelo["upper_95"])) if len(res_modelo["upper_95"]) > 0 else 10.0,
        10.0,
    )

    fig.update_layout(
        template="plotly_white",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#000000", size=11, family="Arial"),
        height=440,
        margin=dict(l=45, r=35, t=55, b=65),
        hovermode="x unified",
        xaxis=dict(
            type="category",
            categoryorder="array",
            categoryarray=eixo_x_cronologico,
            tickangle=-35,
            nticks=16,
            tickfont=dict(size=10, color="#000000"),
            showgrid=False,
        ),
        yaxis=dict(
            title=dict(
                text="<b>Valor (R$)</b>" if is_moeda else "<b>Volume</b>",
                font=dict(size=12, color="#000000"),
            ),
            showgrid=True,
            gridcolor="#e9ecef",
            range=[0, max_y * 1.25],
        ),
        legend=dict(
            orientation="h",
            y=1.15,
            x=0.0,
            xanchor="left",
            font=dict(size=11, color="#000000"),
        ),
    )

    st.plotly_chart(fig, use_container_width=True)


def render_guia_explicativo_modelos():
    """Página completa explicando cada modelo de Data Science e o que ele muda na análise."""
    st.markdown("## 📚 Guia dos Modelos de Previsão & Impacto na Análise")
    st.markdown(
        "Cada algoritmo disponível na aba **🔮 Previsão & Data Science** lê o histórico operacional de uma forma diferente. "
        "Veja abaixo **como cada modelo funciona**, **o que ele muda nos seus KPIs e gráficos** e **quando escolher cada um**."
    )

    st.markdown("---")

    modelos_info = [
        {
            "icone": "🧠",
            "nome": "1. Ensemble Ponderado (Média Inteligente DS) — Padrão Recomendado",
            "badge": "Equilíbrio • Visão Executiva",
            "como_funciona": (
                "Combina os 4 modelos matemáticos simultaneamente com pesos calibrados: "
                "**35% Ridge Sazonal + 30% Regressão Linear (OLS) + 20% Suavização Exponencial (Holt) + 15% Polinomial Amortecido**."
            ),
            "implicacao_analise": (
                "• **Nos gráficos:** Gera uma curva futura suave, mas que ainda respeita as oscilações naturais entre dias da semana.\n"
                "• **Nos KPIs:** Evita tanto o excesso de otimismo quanto quedas bruscas causadas por um único dia atípico (ex.: feriado ou dia sem faturamento).\n"
                "• **Impacto na decisão:** É a projeção mais segura para fechar metas mensais, orçamento de frete e dimensionamento de equipe."
            ),
            "quando_usar": "Reuniões de diretoria, planejamento mensal de faturamento e previsão consolidada de operação.",
        },
        {
            "icone": "📐",
            "nome": "2. Regressão Linear Simples (OLS — Ordinary Least Squares)",
            "badge": "Tendência Reta • Longo Prazo",
            "como_funciona": (
                "Traça uma única linha reta (`y = a + b·t`) atravessando todo o histórico desde o primeiro dia, "
                "calculando o ganho ou perda média diária (`b`) pelo método dos mínimos quadrados."
            ),
            "implicacao_analise": (
                "• **Nos gráficos:** A previsão futura aparece como uma linha reta contínua, ignorando se o dia é segunda-feira ou sábado.\n"
                "• **Nos KPIs:** Dá peso igual aos dados antigos (agosto/setembro) e aos dados recentes (novembro). Se a empresa cresceu muito nos últimos 15 dias, o OLS demora a subir.\n"
                "• **Impacto na decisão:** Mostra se a operação tem crescimento estrutural sólido no trimestre, filtrando ruídos diários."
            ),
            "quando_usar": "Avaliar tendência estrutural de crescimento de faturamento e queda contínua do backlog ao longo dos meses.",
        },
        {
            "icone": "📅",
            "nome": "3. Regressão Ridge (L2) + Sazonalidade por Dia da Semana",
            "badge": "Ciclo Seg–Sáb • Ritmo Operacional",
            "como_funciona": (
                "Usa regularização matemática L2 (evita distorções por outliers) combinada com variáveis para cada dia da semana "
                "(Segunda, Terça, Quarta, Quinta, Sexta e Sábado)."
            ),
            "implicacao_analise": (
                "• **Nos gráficos:** A linha laranja futura sobe e desce em 'dentes de serra' realistas — projetando volumes maiores nos dias fortes da semana e menores nos dias fracos.\n"
                "• **Nos KPIs:** O total da semana ou do mês depende de quantas segundas/sextas ou sábados caem no período projetado.\n"
                "• **Impacto na decisão:** Essencial para escala de separadores, conferentes e agendamento de coletas das transportadoras por dia da semana."
            ),
            "quando_usar": "Planejamento semanal/mensal de Notas Realizadas, Expedição Diária e picos de faturamento por dia da semana.",
        },
        {
            "icone": "📈",
            "nome": "4. Regressão Polinomial Grau 2 (Com Amortecimento de Horizonte)",
            "badge": "Aceleração / Desaceleração • Curvatura",
            "como_funciona": (
                "Ajusta uma parábola (`y = c₂·t² + c₁·t + c₀`) com amortecimento exponencial no futuro (`0,96ᵗ`) "
                "para detectar se o ritmo está acelerando ou perdendo força."
            ),
            "implicacao_analise": (
                "• **Nos gráficos:** A curva futura faz uma leve curvatura para cima (aceleração) ou para baixo (desaceleração) em vez de seguir reta.\n"
                "• **Nos KPIs:** Se os últimos meses aceleraram o faturamento, este modelo projeta valores mais altos que o OLS; se houve desaceleração recente, projeta valores mais conservadores.\n"
                "• **Impacto na decisão:** Ajuda a identificar pontos de virada (inflexão) após mudanças de processo ou entrada de novos clientes."
            ),
            "quando_usar": "Analisar mudança de velocidade operacional (ganho de eficiência na expedição ou desaceleração de pedidos).",
        },
        {
            "icone": "⚡",
            "nome": "5. Suavização Exponencial Dupla (Holt's Linear Trend)",
            "badge": "Memória Curta • Reativo ao Momento Atual",
            "como_funciona": (
                "Atribui peso exponencialmente maior aos últimos dias realizados e peso menor aos meses passados, "
                "atualizando continuamente o nível atual e a tendência recente."
            ),
            "implicacao_analise": (
                "• **Nos gráficos:** A previsão parte exatamente do patamar mais recente da operação, sem ficar presa à média antiga.\n"
                "• **Nos KPIs:** É o modelo mais sensível a mudanças recentes — se o custo de frete ou o backlog caiu drasticamente na última semana, os KPIs futuros refletem isso imediatamente.\n"
                "• **Impacto na decisão:** Ideal para alertas rápidos de curto prazo (próximos 7 dias), mas pode oscilar mais se a última semana teve feriado."
            ),
            "quando_usar": "Monitoramento tático de curto prazo (Próxima Semana) para Backlog, Custo de Frete recente e ritmo imediato de saída.",
        },
    ]

    for m in modelos_info:
        with st.container(border=True):
            c_top1, c_top2 = st.columns([3, 1])
            with c_top1:
                st.markdown(f"#### {m['icone']} {m['nome']}")
            with c_top2:
                st.markdown(
                    f"<div style='text-align:right; padding-top:6px;'>"
                    f"<span style='background:#e0f2fe; color:#0369a1; padding:4px 10px; border-radius:12px; font-size:12px; font-weight:600;'>"
                    f"{m['badge']}</span></div>",
                    unsafe_allow_html=True,
                )
            st.markdown(f"**Como funciona:** {m['como_funciona']}")
            st.markdown(f"**O que implica de diferente na análise:**\n{m['implicacao_analise']}")
            st.markdown(f"**Melhor aplicação no BI:** {m['quando_usar']}")

    st.markdown("---")
    st.markdown("### 📊 Quadro Comparativo: O que muda ao trocar de modelo?")
    df_resumo_modelos = pd.DataFrame(
        [
            {
                "Modelo": "Ensemble Ponderado (Média DS)",
                "Formato da Curva Futura": "Suave + Ciclo Semanal Moderado",
                "Peso nos Dados Recentes": "Equilibrado",
                "Reação a Outliers (Picos)": "Baixa (Protegido)",
                "Impacto Principal nos KPIs": "Projeção mais estável e confiável para metas",
            },
            {
                "Modelo": "Regressão Linear (OLS)",
                "Formato da Curva Futura": "Linha Reta Contínua",
                "Peso nos Dados Recentes": "Igual a todo histórico",
                "Reação a Outliers (Picos)": "Muito Baixa",
                "Impacto Principal nos KPIs": "Mostra a tendência média estrutural de longo prazo",
            },
            {
                "Modelo": "Ridge + Sazonalidade Semanal",
                "Formato da Curva Futura": "Ondulada (Ciclo Seg–Sáb)",
                "Peso nos Dados Recentes": "Moderado",
                "Reação a Outliers (Picos)": "Baixa (Regularizado L2)",
                "Impacto Principal nos KPIs": "Diferencia dias fortes e fracos da semana",
            },
            {
                "Modelo": "Polinomial Grau 2 (Amortecido)",
                "Formato da Curva Futura": "Curva Suave (Parábola Amortecida)",
                "Peso nos Dados Recentes": "Moderado/Alto",
                "Reação a Outliers (Picos)": "Moderada",
                "Impacto Principal nos KPIs": "Capta aceleração ou desaceleração do ritmo",
            },
            {
                "Modelo": "Suavização Exponencial (Holt)",
                "Formato da Curva Futura": "Reta/Amortecida partindo do último nível",
                "Peso nos Dados Recentes": "Muito Alto (Memória Curta)",
                "Reação a Outliers (Picos)": "Alta",
                "Impacto Principal nos KPIs": "Reflete imediatamente o comportamento da última semana",
            },
        ]
    )
    st.dataframe(df_resumo_modelos, use_container_width=True, hide_index=True)


def render_secao_previsao_ds(df_diario: pd.DataFrame, df_frete_tratado: pd.DataFrame = None):
    st.markdown("## 🔮 Previsão & Data Science — Projeções Estatísticas e Regressão")

    subtab_painel, subtab_guia = st.tabs([
        "📊 Painel Preditivo (KPIs, Gráficos & Cronograma)",
        "📚 Explicação dos Modelos & Impacto na Análise",
    ])

    with subtab_guia:
        render_guia_explicativo_modelos()

    with subtab_painel:
        if df_diario is None or df_diario.empty:
            st.info("Aguardando carregamento de dados históricos para gerar previsões.")
            return

        df = df_diario.copy()
        df["DATA"] = pd.to_datetime(df["DATA"], errors="coerce").dt.normalize()
        df = df.dropna(subset=["DATA"]).sort_values("DATA").reset_index(drop=True)
        df = df[df["DATA"].dt.strftime("%d/%m") != "02/01"].reset_index(drop=True)

        # =====================================================================
        # CONTROLES DO MODELO DE DATA SCIENCE
        # =====================================================================
        col_c1, col_c2, col_c3, col_c4 = st.columns([1.2, 1.2, 1.3, 1.0])

        with col_c1:
            horizonte_label = st.selectbox(
                "🔭 Horizonte de Previsão:",
                [
                    "Próxima Semana (7 dias úteis)",
                    "Próximo Mês (22 dias úteis)",
                    "Próximo Trimestre / Acumulado (66 dias úteis)",
                ],
                index=1,
                key="ds_horizonte_sel",
            )

        mapa_horizonte = {
            "Próxima Semana (7 dias úteis)": 7,
            "Próximo Mês (22 dias úteis)": 22,
            "Próximo Trimestre / Acumulado (66 dias úteis)": 66,
        }
        n_dias_prev = mapa_horizonte[horizonte_label]

        with col_c2:
            base_comp_label = st.selectbox(
                "⚖️ Base de Comparação (Benchmark):",
                [
                    "Acumulado Geral (Média Histórica)",
                    "Último Mês Fechado / Atual",
                    "Última Semana Operacional",
                ],
                index=0,
                key="ds_base_comp_sel",
            )

        with col_c3:
            modelo_sel = st.selectbox(
                "🧠 Modelo de Regressão / Previsão:",
                [
                    "Ensemble Ponderado (Média DS)",
                    "Regressão Linear (OLS)",
                    "Ridge + Sazonalidade Semanal",
                    "Polinomial Grau 2 (Amortecido)",
                    "Suavização Exponencial (Holt)",
                ],
                index=0,
                key="ds_modelo_sel",
            )

        with col_c4:
            janela_label = st.selectbox(
                "👁️ Zoom Histórico Gráfico:",
                [
                    "Últimos 30 dias + Previsão",
                    "Todo Histórico + Previsão",
                ],
                index=0,
                key="ds_janela_vis_sel",
            )
        janela_hist_dias = 30 if "30" in janela_label else 0

        # =====================================================================
        # PREPARAÇÃO DAS SÉRIES HISTÓRICAS POR DOMÍNIO
        # =====================================================================
        col_fat_bruto = "Todas as Unidades (Geral)_Fat"
        col_fat_liq = (
            "Todas as Unidades (Geral)_Liq"
            if "Todas as Unidades (Geral)_Liq" in df.columns
            else "Todas as Unidades (Geral)_Fat"
        )
        col_dev = "Todas as Unidades (Geral)_Dev"

        df_fat_hist = df[(df[col_fat_bruto] > 0) | (df[col_dev].abs() > 0)].copy().reset_index(drop=True)
        if df_fat_hist.empty:
            df_fat_hist = df.copy()

        if "Todas as Unidades (Geral)_Liq" not in df.columns:
            df_fat_hist["Fat_Liq_Real"] = df_fat_hist[col_fat_bruto]
            df_fat_hist["Fat_Bruto_Real"] = df_fat_hist[col_fat_bruto] + df_fat_hist[col_dev].abs()
        else:
            df_fat_hist["Fat_Liq_Real"] = df_fat_hist[col_fat_liq]
            df_fat_hist["Fat_Bruto_Real"] = df_fat_hist[col_fat_bruto]

        df_fat_hist["Dev_Real"] = df_fat_hist[col_dev].abs()

        mask_prod = (
            (df.get("Notas_Realizadas", 0) > 0)
            | (df.get("Saudavel", 0) > 0)
            | (df.get("Backlog", 0) > 0)
            | (df.get("Total_Expedidos", 0) > 0)
        )
        df_prod_hist = df[mask_prod].copy().reset_index(drop=True) if mask_prod.any() else df.copy()

        df_frete_hist = df[df.get("Total_Frete", 0) > 0].copy().reset_index(drop=True)
        if df_frete_hist.empty:
            df_frete_hist = df_fat_hist.copy()

        datas_fut_fat = _gerar_proximos_dias_uteis(df_fat_hist["DATA"].max(), n_dias_prev)
        datas_fut_prod = _gerar_proximos_dias_uteis(df_prod_hist["DATA"].max(), n_dias_prev)
        datas_fut_frete = _gerar_proximos_dias_uteis(df_frete_hist["DATA"].max(), n_dias_prev)

        prev_fat_liq = _ajustar_e_prever_serie(
            pd.DatetimeIndex(df_fat_hist["DATA"]),
            df_fat_hist["Fat_Liq_Real"].values,
            datas_fut_fat,
            modelo_sel,
        )
        prev_dev = _ajustar_e_prever_serie(
            pd.DatetimeIndex(df_fat_hist["DATA"]),
            df_fat_hist["Dev_Real"].values,
            datas_fut_fat,
            modelo_sel,
        )
        prev_fat_bruto_vals = prev_fat_liq["forecast"] + prev_dev["forecast"]
        prev_fat_bruto = {
            "hist_fit": prev_fat_liq["hist_fit"] + prev_dev["hist_fit"],
            "forecast": prev_fat_bruto_vals,
            "upper_95": prev_fat_liq["upper_95"] + prev_dev["upper_95"],
            "lower_95": np.maximum(prev_fat_liq["lower_95"] + prev_dev["lower_95"], 0.0),
            "rmse": prev_fat_liq["rmse"],
            "r2": prev_fat_liq["r2"],
            "slope_dia": prev_fat_liq["slope_dia"] + prev_dev["slope_dia"],
        }

        prev_notas = _ajustar_e_prever_serie(
            pd.DatetimeIndex(df_prod_hist["DATA"]),
            df_prod_hist["Notas_Realizadas"].values,
            datas_fut_prod,
            modelo_sel,
        )
        prev_saudavel = _ajustar_e_prever_serie(
            pd.DatetimeIndex(df_prod_hist["DATA"]),
            df_prod_hist["Saudavel"].values,
            datas_fut_prod,
            modelo_sel,
        )
        prev_backlog = _ajustar_e_prever_serie(
            pd.DatetimeIndex(df_prod_hist["DATA"]),
            df_prod_hist["Backlog"].values,
            datas_fut_prod,
            modelo_sel,
        )
        prev_exp = _ajustar_e_prever_serie(
            pd.DatetimeIndex(df_prod_hist["DATA"]),
            df_prod_hist["Total_Expedidos"].values,
            datas_fut_prod,
            modelo_sel,
        )
        prev_skus = _ajustar_e_prever_serie(
            pd.DatetimeIndex(df_prod_hist["DATA"]),
            df_prod_hist["Total_SKUs"].values,
            datas_fut_prod,
            modelo_sel,
        )

        prev_frete = _ajustar_e_prever_serie(
            pd.DatetimeIndex(df_frete_hist["DATA"]),
            df_frete_hist["Total_Frete"].values,
            datas_fut_frete,
            modelo_sel,
        )

        # =====================================================================
        # BENCHMARK (SEMANA, MÊS OU ACUMULADO GERAL)
        # =====================================================================
        def _calc_media_benchmark(df_s: pd.DataFrame, col_nome: str) -> float:
            if df_s.empty or col_nome not in df_s.columns:
                return 0.0
            if base_comp_label == "Última Semana Operacional":
                sub = df_s.tail(6)
            elif base_comp_label == "Último Mês Fechado / Atual":
                ultimo_mes = df_s["DATA"].dt.strftime("%Y-%m").iloc[-1]
                sub = df_s[df_s["DATA"].dt.strftime("%Y-%m") == ultimo_mes]
            else:
                sub = df_s
            return float(sub[col_nome].mean()) if not sub.empty else 0.0

        def _delta_pct_str(media_prev: float, media_ref: float, sufixo: str = "vs. base") -> str:
            if media_ref <= 0:
                return "Base sem histórico"
            diff = ((media_prev - media_ref) / media_ref) * 100
            sinal = "+" if diff >= 0 else ""
            return f"{sinal}{diff:.1f}% {sufixo}"

        # =====================================================================
        # 1. KPIs PROJETADOS — FATURAMENTO & CUSTO DE FRETE
        # =====================================================================
        st.markdown("---")
        st.markdown(f"### 💰 KPIs Financeiros & Frete Projetados ({horizonte_label})")

        tot_fat_bruto_prev = float(np.sum(prev_fat_bruto["forecast"]))
        tot_dev_prev = float(np.sum(prev_dev["forecast"]))
        tot_fat_liq_prev = float(np.sum(prev_fat_liq["forecast"]))
        media_fat_liq_prev = float(np.mean(prev_fat_liq["forecast"]))

        ref_fat_bruto_dia = _calc_media_benchmark(df_fat_hist, "Fat_Bruto_Real")
        ref_fat_liq_dia = _calc_media_benchmark(df_fat_hist, "Fat_Liq_Real")
        ref_dev_dia = _calc_media_benchmark(df_fat_hist, "Dev_Real")

        tot_frete_prev = float(np.sum(prev_frete["forecast"]))
        media_frete_prev = float(np.mean(prev_frete["forecast"]))
        ref_frete_dia = _calc_media_benchmark(df_frete_hist, "Total_Frete")
        pct_frete_fat_prev = (tot_frete_prev / tot_fat_liq_prev * 100) if tot_fat_liq_prev > 0 else 0.0

        kf1, kf2, kf3, kf4, kf5 = st.columns(5)
        kf1.metric(
            "💰 Faturamento Bruto Previsto",
            _fmt_brl(tot_fat_bruto_prev),
            delta=_delta_pct_str(tot_fat_bruto_prev / n_dias_prev, ref_fat_bruto_dia),
        )
        kf2.metric(
            "↩️ Devoluções Previstas",
            _fmt_brl(-tot_dev_prev),
            delta=_delta_pct_str(tot_dev_prev / n_dias_prev, ref_dev_dia),
            delta_color="inverse",
        )
        kf3.metric(
            "💵 Faturamento Líquido Previsto",
            _fmt_brl(tot_fat_liq_prev),
            delta=_delta_pct_str(media_fat_liq_prev, ref_fat_liq_dia),
        )
        kf4.metric(
            "📊 Média Diária Líquida Prevista",
            _fmt_brl(media_fat_liq_prev),
            delta=f"Tendência: {_fmt_brl(prev_fat_liq['slope_dia'])}/dia",
            delta_color="off",
        )
        kf5.metric(
            "🚚 Custo de Frete Previsto",
            _fmt_brl(tot_frete_prev),
            delta=f"{pct_frete_fat_prev:.2f}% do Fat. Líquido ({_delta_pct_str(media_frete_prev, ref_frete_dia)})",
            delta_color="inverse",
        )

        # =====================================================================
        # 2. KPIs PROJETADOS — PRODUÇÃO & EXPEDIÇÃO
        # =====================================================================
        st.markdown(f"### 🏭 KPIs Operacionais Projetados — Produção & Expedição ({horizonte_label})")

        tot_notas_prev = float(np.sum(prev_notas["forecast"]))
        tot_saud_prev = float(np.sum(prev_saudavel["forecast"]))
        tot_back_prev = float(np.sum(prev_backlog["forecast"]))
        tot_exp_prev = float(np.sum(prev_exp["forecast"]))
        tot_skus_prev = float(np.sum(prev_skus["forecast"]))

        ref_notas_dia = _calc_media_benchmark(df_prod_hist, "Notas_Realizadas")
        ref_saud_dia = _calc_media_benchmark(df_prod_hist, "Saudavel")
        ref_back_dia = _calc_media_benchmark(df_prod_hist, "Backlog")
        ref_exp_dia = _calc_media_benchmark(df_prod_hist, "Total_Expedidos")
        ref_skus_dia = _calc_media_benchmark(df_prod_hist, "Total_SKUs")

        kp1, kp2, kp3, kp4, kp5 = st.columns(5)
        kp1.metric(
            "📦 Notas Realizadas Previstas",
            _fmt_int(tot_notas_prev),
            delta=f"Média {tot_notas_prev / n_dias_prev:,.1f}/dia ({_delta_pct_str(tot_notas_prev / n_dias_prev, ref_notas_dia)})".replace(",", "."),
        )
        kp2.metric(
            "🟢 Notas Saudáveis Previstas",
            _fmt_int(tot_saud_prev),
            delta=f"Média {tot_saud_prev / n_dias_prev:,.1f}/dia ({_delta_pct_str(tot_saud_prev / n_dias_prev, ref_saud_dia)})".replace(",", "."),
        )
        kp3.metric(
            "🔴 Backlog Previsto",
            _fmt_int(tot_back_prev),
            delta=f"Média {tot_back_prev / n_dias_prev:,.1f}/dia ({_delta_pct_str(tot_back_prev / n_dias_prev, ref_back_dia)})".replace(",", "."),
            delta_color="inverse",
        )
        kp4.metric(
            "🚚 Volume Expedido Previsto",
            _fmt_int(tot_exp_prev),
            delta=f"Média {tot_exp_prev / n_dias_prev:,.1f}/dia ({_delta_pct_str(tot_exp_prev / n_dias_prev, ref_exp_dia)})".replace(",", "."),
        )
        kp5.metric(
            "🏷️ SKUs Separados Previstos",
            _fmt_int(tot_skus_prev),
            delta=f"Média {tot_skus_prev / n_dias_prev:,.1f}/dia ({_delta_pct_str(tot_skus_prev / n_dias_prev, ref_skus_dia)})".replace(",", "."),
        )

        # =====================================================================
        # 3. GRÁFICOS PREDITIVOS DE FATURAMENTO & COMPARATIVO ENTRE MODELOS
        # =====================================================================
        st.markdown("---")
        _plot_serie_previsao(
            f"📈 Projeção de Faturamento Líquido ({modelo_sel}) — Próximos {n_dias_prev} Dias Úteis",
            pd.DatetimeIndex(df_fat_hist["DATA"]),
            df_fat_hist["Fat_Liq_Real"].values,
            prev_fat_liq,
            datas_fut_fat,
            cor_hist="#1f77b4",
            cor_prev="#d97706",
            is_moeda=True,
            janela_hist=janela_hist_dias,
        )

        with st.expander("🔬 Comparativo Técnico entre Modelos de Regressão (Média Diária & Total Projetado)", expanded=True):
            rows_comp = []
            for nome_m, vals_m in prev_fat_liq["modelos_detalhe"].items():
                tot_m_liq = float(np.sum(vals_m))
                med_m_liq = float(np.mean(vals_m))
                tot_m_notas = float(np.sum(prev_notas["modelos_detalhe"][nome_m]))
                tot_m_exp = float(np.sum(prev_exp["modelos_detalhe"][nome_m]))
                tot_m_frete = float(np.sum(prev_frete["modelos_detalhe"][nome_m]))
                rows_comp.append(
                    {
                        "Modelo de Data Science": nome_m,
                        "Média Diária Fat. Líquido": _fmt_brl(med_m_liq),
                        f"Total Fat. Líquido ({n_dias_prev}d)": _fmt_brl(tot_m_liq),
                        "Var. vs. Benchmark": _delta_pct_str(med_m_liq, ref_fat_liq_dia, ""),
                        f"Notas Realizadas ({n_dias_prev}d)": _fmt_int(tot_m_notas),
                        f"Volume Expedido ({n_dias_prev}d)": _fmt_int(tot_m_exp),
                        f"Custo Frete ({n_dias_prev}d)": _fmt_brl(tot_m_frete),
                    }
                )
            st.dataframe(pd.DataFrame(rows_comp), use_container_width=True, hide_index=True)

        # =====================================================================
        # 4. GRÁFICOS PREDITIVOS DE PRODUÇÃO, EXPEDIÇÃO & CUSTO DE FRETE
        # =====================================================================
        st.markdown("---")
        col_g1, col_g2 = st.columns(2)

        with col_g1:
            _plot_serie_previsao(
                f"📦 Projeção de Notas Realizadas / PVs ({modelo_sel})",
                pd.DatetimeIndex(df_prod_hist["DATA"]),
                df_prod_hist["Notas_Realizadas"].values,
                prev_notas,
                datas_fut_prod,
                cor_hist="#1f77b4",
                cor_prev="#16a34a",
                is_moeda=False,
                janela_hist=janela_hist_dias,
            )

        with col_g2:
            _plot_serie_previsao(
                f"🚚 Projeção de Volume Expedido ({modelo_sel})",
                pd.DatetimeIndex(df_prod_hist["DATA"]),
                df_prod_hist["Total_Expedidos"].values,
                prev_exp,
                datas_fut_prod,
                cor_hist="#0284c7",
                cor_prev="#ea580c",
                is_moeda=False,
                janela_hist=janela_hist_dias,
            )

        col_g3, col_g4 = st.columns(2)

        with col_g3:
            _plot_serie_previsao(
                f"🔴 Projeção de Backlog Operacional ({modelo_sel})",
                pd.DatetimeIndex(df_prod_hist["DATA"]),
                df_prod_hist["Backlog"].values,
                prev_backlog,
                datas_fut_prod,
                cor_hist="#dc2626",
                cor_prev="#991b1b",
                is_moeda=False,
                janela_hist=janela_hist_dias,
            )

        with col_g4:
            _plot_serie_previsao(
                f"💸 Projeção de Custo de Frete Terceirizado ({modelo_sel})",
                pd.DatetimeIndex(df_frete_hist["DATA"]),
                df_frete_hist["Total_Frete"].values,
                prev_frete,
                datas_fut_frete,
                cor_hist="#7c3aed",
                cor_prev="#d97706",
                is_moeda=True,
                janela_hist=janela_hist_dias,
            )

        # =====================================================================
        # 5. TABELA CONSOLIDADA DIÁRIA DAS PREVISÕES & EXPORTAÇÃO CSV
        # =====================================================================
        st.markdown("---")
        st.markdown(f"### 📋 Cronograma Diário Projetado ({horizonte_label} — {modelo_sel})")

        df_prev_tabela = pd.DataFrame(
            {
                "Data Projetada": datas_fut_fat.strftime("%d/%m/%Y"),
                "Dia da Semana": datas_fut_fat.dayofweek.map(
                    {0: "Segunda", 1: "Terça", 2: "Quarta", 3: "Quinta", 4: "Sexta", 5: "Sábado"}
                ),
                "Fat. Bruto Previsto": [_fmt_brl(v) for v in prev_fat_bruto["forecast"]],
                "Devoluções Previstas": [_fmt_brl(-v) for v in prev_dev["forecast"]],
                "Fat. Líquido Previsto": [_fmt_brl(v) for v in prev_fat_liq["forecast"]],
                "IC 95% Mínimo": [_fmt_brl(v) for v in prev_fat_liq["lower_95"]],
                "IC 95% Máximo": [_fmt_brl(v) for v in prev_fat_liq["upper_95"]],
                "Notas Previstas": [_fmt_int(v) for v in prev_notas["forecast"]],
                "Saudáveis Previstas": [_fmt_int(v) for v in prev_saudavel["forecast"]],
                "Backlog Previsto": [_fmt_int(v) for v in prev_backlog["forecast"]],
                "Expedição Prevista": [_fmt_int(v) for v in prev_exp["forecast"]],
                "Custo Frete Previsto": [_fmt_brl(v) for v in prev_frete["forecast"]],
            }
        )

        st.dataframe(df_prev_tabela, use_container_width=True, height=420, hide_index=True)

        csv_prev = df_prev_tabela.to_csv(index=False, sep=";").encode("utf-8-sig")
        st.download_button(
            label="📥 Baixar Previsões Projetadas (CSV)",
            data=csv_prev,
            file_name=f"Previsoes_BI_{n_dias_prev}_dias.csv",
            mime="text/csv",
        )