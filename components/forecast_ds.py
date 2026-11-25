import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
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


def _gerar_dias_uteis_periodo(data_inicio: pd.Timestamp, data_fim: pd.Timestamp) -> pd.DatetimeIndex:
    """Gera todos os dias operacionais (segunda a sábado) dentro do intervalo [data_inicio, data_fim]."""
    if data_fim < data_inicio:
        data_fim = data_inicio
    todos = pd.date_range(start=data_inicio, end=data_fim, freq="D")
    uteis = [d for d in todos if d.weekday() != 6]
    return pd.DatetimeIndex(uteis if uteis else [data_inicio])


def _gerar_proximos_n_dias_uteis(ultima_data: pd.Timestamp, n_dias: int) -> pd.DatetimeIndex:
    """Gera os próximos N dias operacionais (segunda a sábado, excluindo domingos)."""
    datas = []
    curr = pd.Timestamp(ultima_data) + pd.Timedelta(days=1)
    while len(datas) < n_dias:
        if curr.weekday() != 6:
            datas.append(curr)
        curr += pd.Timedelta(days=1)
    return pd.DatetimeIndex(datas)


def _treinar_e_prever_datas(
    datas_treino: pd.DatetimeIndex,
    valores_treino: np.ndarray,
    datas_alvo: pd.DatetimeIndex,
    modelo_escolhido: str,
) -> dict:
    """
    Treina os 5 modelos de Data Science (OLS, Ridge Sazonal, Polinomial Grau 2 Amortecido, Holt Linear e Ensemble)
    sobre `datas_treino` e projeta exatamente para `datas_alvo`.
    """
    y = np.asarray(valores_treino, dtype=float)
    n = len(y)
    h = len(datas_alvo)

    if n < 3 or h == 0:
        media_const = float(np.mean(y)) if n > 0 else 0.0
        fut_const = np.full(max(h, 1), max(media_const, 0.0))
        return {
            "forecast": fut_const,
            "upper_95": fut_const * 1.15,
            "lower_95": np.maximum(fut_const * 0.85, 0.0),
            "rmse": 0.0,
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
    dt_base = pd.Timestamp(datas_treino[0])
    dias_corridos_treino = np.maximum((datas_treino - dt_base).days.values.astype(float), 0.0)
    escala_dia_util = (n - 1) / max(float(dias_corridos_treino[-1]), 1.0)
    t_alvo = np.maximum((datas_alvo - dt_base).days.values.astype(float) * escala_dia_util, 0.0)

    # 1. Regressão Linear Simples (OLS)
    b_ols, a_ols = np.polyfit(t, y, 1)
    fit_ols = a_ols + b_ols * t
    pred_ols = np.maximum(a_ols + b_ols * t_alvo, 0.0)

    # 2. Regressão Ridge (L2) + Sazonalidade por Dia da Semana
    dows_all = list(range(6))
    t_scale = max(float(n), 1.0)

    def _build_X(idx_t: np.ndarray, dts: pd.DatetimeIndex) -> np.ndarray:
        cols = [np.ones(len(idx_t)), idx_t / t_scale]
        for d in dows_all[1:]:
            cols.append((dts.dayofweek == d).astype(float))
        return np.column_stack(cols)

    X_hist = _build_X(t, datas_treino)
    X_alvo = _build_X(t_alvo, datas_alvo)

    lam = 1.5
    reg = np.eye(X_hist.shape[1]) * lam
    reg[0, 0] = 0.0
    beta_ridge = np.linalg.solve(X_hist.T @ X_hist + reg, X_hist.T @ y)

    fit_ridge = X_hist @ beta_ridge
    pred_ridge = np.maximum(X_alvo @ beta_ridge, 0.0)

    # 3. Regressão Polinomial Grau 2 (Com Amortecimento no horizonte futuro)
    if n >= 6:
        c2, c1, c0 = np.polyfit(t, y, 2)
        fit_poly = c2 * (t**2) + c1 * t + c0
        t_alvo_damp = np.where(
            t_alvo <= (n - 1),
            t_alvo,
            (n - 1) + (t_alvo - (n - 1)) * 0.65,
        )
        pred_poly = np.maximum(c2 * (t_alvo_damp**2) + c1 * t_alvo_damp + c0, 0.0)
    else:
        fit_poly = fit_ols.copy()
        pred_poly = pred_ols.copy()

    # 4. Suavização Exponencial Dupla (Holt's Linear Trend)
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
    for idx_i, tv in enumerate(t_alvo):
        if tv <= (n - 1):
            idx_near = int(np.clip(round(tv), 0, n - 1))
            pred_holt[idx_i] = max(fit_holt[idx_near], 0.0)
        else:
            step = max(int(round(tv - (n - 1))), 1)
            phi_sum = sum(phi**k for k in range(1, min(step, 60) + 1))
            pred_holt[idx_i] = max(level + phi_sum * trend, 0.0)

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

    fator_h = np.sqrt(1.0 + (np.arange(1, h + 1) / max(n, 1)))
    margem_95 = 1.96 * rmse * fator_h * 0.45

    return {
        "forecast": pred_sel,
        "upper_95": np.maximum(pred_sel + margem_95, pred_sel),
        "lower_95": np.maximum(pred_sel - margem_95, 0.0),
        "rmse": rmse,
        "slope_dia": float(b_ols),
        "modelos_detalhe": {k: v[1] for k, v in mapa_modelos.items()},
    }


def _plot_somente_previsao_multi(
    titulo: str,
    datas_fut: pd.DatetimeIndex,
    series_dict: list,
    is_moeda: bool = True,
    altura: int = 440,
    modo_rotulos: str = "Automático (Anti-Sobreposição)",
):
    """
    Plota EXCLUSIVAMENTE os dias projetados, com sistema anti-sobreposição de rótulos:
    - Barras exibem valores DENTRO do topo da barra (branco em negrito), liberando a área externa.
    - Linhas principais exibem valores ACIMA dos marcadores (top center).
    - Séries secundárias de menor escala (ex.: Devoluções, Backlog) usam eixo secundário (yaxis2)
      quando solicitado para nunca ficarem achatadas na base.
    """
    st.markdown(f"#### {titulo}")

    usa_eixo2 = any(s.get("eixo_secundario", False) for s in series_dict)
    fig = make_subplots(specs=[[{"secondary_y": usa_eixo2}]])

    dias_sem = {0: "Seg", 1: "Ter", 2: "Qua", 3: "Qui", 4: "Sex", 5: "Sáb", 6: "Dom"}
    x_labels = [f"{d.strftime('%d/%m')} ({dias_sem[d.weekday()]})" for d in datas_fut]
    fmt_hover = "R$ %{y:,.2f}" if is_moeda else "%{y:,.1f}"

    n_pts = len(x_labels)
    qtd_linhas = sum(1 for s in series_dict if s.get("tipo", "linha") != "barra")

    max_y1 = 10.0
    max_y2 = 10.0

    idx_linha_atual = 0
    for s in series_dict:
        vals = np.asarray(s["valores"], dtype=float)
        is_sec = s.get("eixo_secundario", False)
        if len(vals) > 0:
            if is_sec:
                max_y2 = max(max_y2, float(np.max(vals)))
            else:
                max_y1 = max(max_y1, float(np.max(vals)))

        if modo_rotulos == "Apenas Hover (Limpo)":
            mostrar_texto = [False] * n_pts
        elif modo_rotulos == "Mostrar Todos":
            mostrar_texto = [True] * n_pts
        else:
            if n_pts <= 8:
                mostrar_texto = [True] * n_pts
            elif n_pts <= 14:
                mostrar_texto = [(i % 2 == 0 or i == n_pts - 1) for i in range(n_pts)]
            else:
                mostrar_texto = [(i % 3 == 0 or i == n_pts - 1) for i in range(n_pts)]

        textos = [
            (_fmt_brl_compacto(v) if is_moeda else _fmt_int(v)) if mostrar_texto[i] else ""
            for i, v in enumerate(vals)
        ]

        if s.get("tipo", "linha") == "barra":
            pos_barra = "inside" if qtd_linhas > 0 else "outside"
            cor_txt_barra = "#ffffff" if pos_barra == "inside" else "#000000"

            fig.add_trace(
                go.Bar(
                    x=x_labels,
                    y=vals,
                    name=s["nome"],
                    marker_color=s["cor"],
                    opacity=0.86,
                    text=textos,
                    textposition=pos_barra,
                    insidetextanchor="end",
                    textfont=dict(size=10, color=cor_txt_barra, family="Arial Black"),
                    cliponaxis=False,
                    hovertemplate=f"<b>%{{x}}</b><br>{s['nome']}: {fmt_hover}<extra></extra>",
                ),
                secondary_y=is_sec,
            )
        else:
            if is_sec:
                pos_linha = "top center"
            elif idx_linha_atual == 0:
                pos_linha = "top center"
            else:
                pos_linha = "bottom center"
            idx_linha_atual += 1

            if modo_rotulos == "Automático (Anti-Sobreposição)" and n_pts > 10 and is_sec:
                textos_linha = [""] * n_pts
                modo_scatter = "lines+markers"
            else:
                textos_linha = textos
                modo_scatter = "lines+markers+text" if any(textos_linha) else "lines+markers"

            fig.add_trace(
                go.Scatter(
                    x=x_labels,
                    y=vals,
                    mode=modo_scatter,
                    name=s["nome"],
                    line=dict(color=s["cor"], width=3.0, dash=s.get("dash", "solid")),
                    marker=dict(size=7 if n_pts <= 12 else 5, symbol=s.get("symbol", "circle")),
                    text=textos_linha,
                    textposition=pos_linha,
                    textfont=dict(size=10, color=s["cor"], family="Arial Black"),
                    cliponaxis=False,
                    hovertemplate=f"<b>%{{x}}</b><br>{s['nome']}: {fmt_hover}<extra></extra>",
                ),
                secondary_y=is_sec,
            )

        if "upper_95" in s and "lower_95" in s:
            up = np.asarray(s["upper_95"], dtype=float)
            lo = np.asarray(s["lower_95"], dtype=float)
            if len(up) > 0:
                max_y1 = max(max_y1, float(np.max(up)))
            fig.add_trace(
                go.Scatter(
                    x=x_labels + x_labels[::-1],
                    y=list(up) + list(lo[::-1]),
                    fill="toself",
                    fillcolor="rgba(217, 119, 6, 0.11)",
                    line=dict(color="rgba(255,255,255,0)"),
                    hoverinfo="skip",
                    name="Intervalo Confiança 95%",
                ),
                secondary_y=False,
            )

    fig.update_layout(
        template="plotly_white",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#000000", size=11, family="Arial"),
        height=altura,
        barmode="group",
        margin=dict(l=45, r=45 if usa_eixo2 else 30, t=55, b=75),
        hovermode="x unified",
        xaxis=dict(
            type="category",
            categoryorder="array",
            categoryarray=x_labels,
            tickangle=-35,
            tickfont=dict(size=10, color="#000000"),
            showgrid=False,
        ),
        legend=dict(orientation="h", y=1.16, x=0.0, xanchor="left", font=dict(size=11, color="#000000")),
    )

    fig.update_yaxes(
        title_text="<b>Valor Projetado (R$)</b>" if is_moeda else "<b>Volume Projetado</b>",
        showgrid=True,
        gridcolor="#e9ecef",
        range=[0, max_y1 * 1.28],
        secondary_y=False,
    )

    if usa_eixo2:
        fig.update_yaxes(
            title_text="<b>Devoluções (R$)</b>" if is_moeda else "<b>Backlog (Qtd)</b>",
            showgrid=False,
            range=[0, max_y2 * 2.2],
            secondary_y=True,
        )

    st.plotly_chart(fig, use_container_width=True)


def render_guia_explicativo_modelos():
    """Sub-aba integrada explicando cada modelo de Data Science e seu impacto analítico."""
    st.markdown("### 📚 Modelos de Data Science & Impacto na Análise")
    st.markdown(
        "Entenda como cada algoritmo matemático lê os dados da operação e o que muda nas projeções quando você alterna entre eles:"
    )

    modelos_info = [
        {
            "icone": "🧠",
            "nome": "1. Ensemble Ponderado (Média Inteligente DS) — Recomendado",
            "badge": "Equilíbrio • Visão Executiva",
            "como_funciona": (
                "Combina os 4 modelos simultaneamente (**35% Ridge Sazonal + 30% Regressão Linear OLS + "
                "20% Suavização Exponencial Holt + 15% Polinomial Amortecido**)."
            ),
            "implicacao_analise": (
                "• **Nos gráficos:** Gera projeções equilibradas que absorvem o ritmo semanal sem exagerar picos isolados.\n"
                "• **Nos KPIs:** É o modelo mais seguro para metas mensais, orçamento de frete e dimensionamento de equipe."
            ),
        },
        {
            "icone": "📐",
            "nome": "2. Regressão Linear Simples (OLS — Ordinary Least Squares)",
            "badge": "Tendência Reta • Longo Prazo",
            "como_funciona": "Ajusta uma linha reta (`y = a + b·t`) sobre todo o histórico observado desde o primeiro dia.",
            "implicacao_analise": (
                "• **Nos gráficos:** Linha reta contínua, sem diferenciar segunda-feira de sábado.\n"
                "• **Nos KPIs:** Mede a tendência estrutural de longo prazo, ignorando oscilações de curto prazo."
            ),
        },
        {
            "icone": "📅",
            "nome": "3. Regressão Ridge (L2) + Sazonalidade por Dia da Semana",
            "badge": "Ciclo Seg–Sáb • Ritmo Diário",
            "como_funciona": "Combina tendência regularizada (L2) com variáveis para cada dia operacional da semana (Segunda a Sábado).",
            "implicacao_analise": (
                "• **Nos gráficos:** Sobe nos dias fortes da semana e cai aos sábados, refletindo o ritmo real do galpão.\n"
                "• **Nos KPIs:** Ideal para escala diária de separação, conferência e agendamento de coletas."
            ),
        },
        {
            "icone": "📈",
            "nome": "4. Regressão Polinomial Grau 2 (Com Amortecimento)",
            "badge": "Aceleração / Desaceleração",
            "como_funciona": "Ajusta uma parábola (`y = c₂·t² + c₁·t + c₀`) com amortecimento no horizonte futuro.",
            "implicacao_analise": (
                "• **Nos gráficos:** Faz curvatura suave indicando ganho de aceleração ou perda de ritmo recente.\n"
                "• **Nos KPIs:** Captura pontos de virada quando novos clientes ou processos alteram a velocidade."
            ),
        },
        {
            "icone": "⚡",
            "nome": "5. Suavização Exponencial Dupla (Holt's Linear Trend)",
            "badge": "Memória Curta • Reativo",
            "como_funciona": "Dá peso exponencialmente maior aos dias mais recentes do que aos meses passados.",
            "implicacao_analise": (
                "• **Nos gráficos:** Parte diretamente do patamar mais recente da operação.\n"
                "• **Nos KPIs:** Reage rápido a mudanças recentes no Backlog, Frete ou Expedição."
            ),
        },
    ]

    for m in modelos_info:
        with st.container(border=True):
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(f"#### {m['icone']} {m['nome']}")
            with c2:
                st.markdown(
                    f"<div style='text-align:right; padding-top:6px;'>"
                    f"<span style='background:#e0f2fe; color:#0369a1; padding:4px 10px; border-radius:12px; font-size:12px; font-weight:600;'>"
                    f"{m['badge']}</span></div>",
                    unsafe_allow_html=True,
                )
            st.markdown(f"**Como funciona:** {m['como_funciona']}")
            st.markdown(f"**O que muda na análise:**\n{m['implicacao_analise']}")


def render_secao_previsao_ds(df_diario: pd.DataFrame, df_frete_tratado: pd.DataFrame = None):
    st.markdown("## 🔮 Previsão & Data Science — Projeções Estatísticas e Regressão")

    subtab_proj, subtab_modelos = st.tabs([
        "📊 Projeções Futuras (KPIs & Gráficos)",
        "📚 Modelos & Impacto Analítico",
    ])

    with subtab_modelos:
        render_guia_explicativo_modelos()

    with subtab_proj:
        if df_diario is None or df_diario.empty:
            st.info("Aguardando carregamento de dados históricos para gerar previsões.")
            return

        df = df_diario.copy()
        df["DATA"] = pd.to_datetime(df["DATA"], errors="coerce").dt.normalize()
        df = df.dropna(subset=["DATA"]).sort_values("DATA").reset_index(drop=True)
        df = df[df["DATA"].dt.strftime("%d/%m") != "02/01"].reset_index(drop=True)

        ultima_data_base = df["DATA"].max()

        # =====================================================================
        # CONTROLES DE INTERVALO, BENCHMARK, MODELO E LEITURA DE RÓTULOS
        # =====================================================================
        col_c1, col_c2, col_c3, col_c4 = st.columns([1.25, 1.15, 1.3, 1.15])

        with col_c1:
            modo_periodo = st.selectbox(
                "🔭 Intervalo da Projeção:",
                [
                    "Próxima Semana (6 dias úteis)",
                    "Próximo Mês (22 dias úteis)",
                    "Intervalo de Calendário Específico",
                ],
                index=0,
                key="ds_modo_periodo_sel",
            )

        with col_c2:
            base_comp_label = st.selectbox(
                "⚖️ Base de Comparação (KPIs):",
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
            modo_rotulos = st.selectbox(
                "🏷️ Rótulos nos Gráficos:",
                [
                    "Automático (Anti-Sobreposição)",
                    "Mostrar Todos",
                    "Apenas Hover (Limpo)",
                ],
                index=0,
                key="ds_modo_rotulos_sel",
            )

        if modo_periodo == "Intervalo de Calendário Específico":
            dt_default_ini = (ultima_data_base + pd.Timedelta(days=1)).date()
            dt_default_fim = (ultima_data_base + pd.Timedelta(days=15)).date()
            sel_datas = st.date_input(
                "📅 Selecione os dias específicos para acompanhar a projeção:",
                value=(dt_default_ini, dt_default_fim),
                min_value=dt_default_ini,
                key="ds_cal_especifico",
            )
            if isinstance(sel_datas, tuple) and len(sel_datas) == 2:
                datas_alvo = _gerar_dias_uteis_periodo(pd.Timestamp(sel_datas[0]), pd.Timestamp(sel_datas[1]))
            else:
                datas_alvo = _gerar_dias_uteis_periodo(pd.Timestamp(dt_default_ini), pd.Timestamp(dt_default_fim))
        elif "Semana" in modo_periodo:
            datas_alvo = _gerar_proximos_n_dias_uteis(ultima_data_base, 6)
        else:
            datas_alvo = _gerar_proximos_n_dias_uteis(ultima_data_base, 22)

        n_dias_prev = len(datas_alvo)

        # =====================================================================
        # PREPARAÇÃO DAS SÉRIES HISTÓRICAS PARA TREINO
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

        prev_fat_liq = _treinar_e_prever_datas(
            pd.DatetimeIndex(df_fat_hist["DATA"]),
            df_fat_hist["Fat_Liq_Real"].values,
            datas_alvo,
            modelo_sel,
        )
        prev_dev = _treinar_e_prever_datas(
            pd.DatetimeIndex(df_fat_hist["DATA"]),
            df_fat_hist["Dev_Real"].values,
            datas_alvo,
            modelo_sel,
        )
        prev_fat_bruto_vals = prev_fat_liq["forecast"] + prev_dev["forecast"]

        prev_notas = _treinar_e_prever_datas(
            pd.DatetimeIndex(df_prod_hist["DATA"]),
            df_prod_hist["Notas_Realizadas"].values,
            datas_alvo,
            modelo_sel,
        )
        prev_saudavel = _treinar_e_prever_datas(
            pd.DatetimeIndex(df_prod_hist["DATA"]),
            df_prod_hist["Saudavel"].values,
            datas_alvo,
            modelo_sel,
        )
        prev_backlog = _treinar_e_prever_datas(
            pd.DatetimeIndex(df_prod_hist["DATA"]),
            df_prod_hist["Backlog"].values,
            datas_alvo,
            modelo_sel,
        )
        prev_exp = _treinar_e_prever_datas(
            pd.DatetimeIndex(df_prod_hist["DATA"]),
            df_prod_hist["Total_Expedidos"].values,
            datas_alvo,
            modelo_sel,
        )
        prev_skus = _treinar_e_prever_datas(
            pd.DatetimeIndex(df_prod_hist["DATA"]),
            df_prod_hist["Total_SKUs"].values,
            datas_alvo,
            modelo_sel,
        )
        prev_frete = _treinar_e_prever_datas(
            pd.DatetimeIndex(df_frete_hist["DATA"]),
            df_frete_hist["Total_Frete"].values,
            datas_alvo,
            modelo_sel,
        )

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

        def _delta_pct_str(media_prev: float, media_ref: float) -> str:
            if media_ref <= 0:
                return "Sem base"
            diff = ((media_prev - media_ref) / media_ref) * 100
            sinal = "+" if diff >= 0 else ""
            return f"{sinal}{diff:.1f}% vs. base"

        periodo_str = f"{datas_alvo[0].strftime('%d/%m/%Y')} a {datas_alvo[-1].strftime('%d/%m/%Y')} ({n_dias_prev} dias úteis)"

        # =====================================================================
        # BLOCO 1 — KPIs FINANCEIROS + GRÁFICOS FINANCEIROS SEPARADOS
        # =====================================================================
        st.markdown("---")
        st.markdown(f"### 💰 Bloco Financeiro Projetado — {periodo_str}")

        tot_fat_bruto_prev = float(np.sum(prev_fat_bruto_vals))
        tot_dev_prev = float(np.sum(prev_dev["forecast"]))
        tot_fat_liq_prev = float(np.sum(prev_fat_liq["forecast"]))
        media_fat_liq_prev = float(np.mean(prev_fat_liq["forecast"]))
        tot_frete_prev = float(np.sum(prev_frete["forecast"]))
        pct_frete_fat_prev = (tot_frete_prev / tot_fat_liq_prev * 100) if tot_fat_liq_prev > 0 else 0.0

        kf1, kf2, kf3, kf4, kf5 = st.columns(5)
        kf1.metric(
            "💰 Faturamento Bruto Previsto",
            _fmt_brl(tot_fat_bruto_prev),
            delta=_delta_pct_str(tot_fat_bruto_prev / n_dias_prev, _calc_media_benchmark(df_fat_hist, "Fat_Bruto_Real")),
        )
        kf2.metric(
            "↩️ Devoluções Previstas",
            _fmt_brl(-tot_dev_prev),
            delta=_delta_pct_str(tot_dev_prev / n_dias_prev, _calc_media_benchmark(df_fat_hist, "Dev_Real")),
            delta_color="inverse",
        )
        kf3.metric(
            "💵 Faturamento Líquido Previsto",
            _fmt_brl(tot_fat_liq_prev),
            delta=_delta_pct_str(media_fat_liq_prev, _calc_media_benchmark(df_fat_hist, "Fat_Liq_Real")),
        )
        kf4.metric(
            "📊 Média Diária Líquida",
            _fmt_brl(media_fat_liq_prev),
            delta=f"Tendência: {_fmt_brl(prev_fat_liq['slope_dia'])}/dia",
            delta_color="off",
        )
        kf5.metric(
            "🚚 Custo de Frete Previsto",
            _fmt_brl(tot_frete_prev),
            delta=f"{pct_frete_fat_prev:.2f}% do Fat. Líquido",
            delta_color="inverse",
        )

        if n_dias_prev > 10:
            _plot_somente_previsao_multi(
                f"📈 Previsão Diária: Faturamento Bruto, Líquido & Devoluções ({modelo_sel})",
                datas_alvo,
                [
                    {"nome": "Faturamento Bruto", "valores": prev_fat_bruto_vals, "cor": "#1f77b4", "tipo": "barra"},
                    {
                        "nome": "Faturamento Líquido",
                        "valores": prev_fat_liq["forecast"],
                        "cor": "#16a34a",
                        "tipo": "linha",
                        "upper_95": prev_fat_liq["upper_95"],
                        "lower_95": prev_fat_liq["lower_95"],
                    },
                    {
                        "nome": "Devoluções (Eixo Dir.)",
                        "valores": prev_dev["forecast"],
                        "cor": "#dc2626",
                        "tipo": "linha",
                        "dash": "dot",
                        "eixo_secundario": True,
                    },
                ],
                is_moeda=True,
                altura=450,
                modo_rotulos=modo_rotulos,
            )
            _plot_somente_previsao_multi(
                f"💸 Previsão Diária: Custo de Frete Terceirizado ({modelo_sel})",
                datas_alvo,
                [
                    {"nome": "Custo Frete Previsto", "valores": prev_frete["forecast"], "cor": "#7c3aed", "tipo": "barra"},
                ],
                is_moeda=True,
                altura=380,
                modo_rotulos=modo_rotulos,
            )
        else:
            col_fin1, col_fin2 = st.columns([1.4, 1.0])
            with col_fin1:
                _plot_somente_previsao_multi(
                    f"📈 Previsão Diária: Faturamento Bruto, Líquido & Devoluções ({modelo_sel})",
                    datas_alvo,
                    [
                        {"nome": "Faturamento Bruto", "valores": prev_fat_bruto_vals, "cor": "#1f77b4", "tipo": "barra"},
                        {
                            "nome": "Faturamento Líquido",
                            "valores": prev_fat_liq["forecast"],
                            "cor": "#16a34a",
                            "tipo": "linha",
                            "upper_95": prev_fat_liq["upper_95"],
                            "lower_95": prev_fat_liq["lower_95"],
                        },
                        {
                            "nome": "Devoluções (Eixo Dir.)",
                            "valores": prev_dev["forecast"],
                            "cor": "#dc2626",
                            "tipo": "linha",
                            "dash": "dot",
                            "eixo_secundario": True,
                        },
                    ],
                    is_moeda=True,
                    altura=440,
                    modo_rotulos=modo_rotulos,
                )

            with col_fin2:
                _plot_somente_previsao_multi(
                    f"💸 Previsão Diária: Custo de Frete Terceirizado ({modelo_sel})",
                    datas_alvo,
                    [
                        {"nome": "Custo Frete Previsto", "valores": prev_frete["forecast"], "cor": "#7c3aed", "tipo": "barra"},
                    ],
                    is_moeda=True,
                    altura=440,
                    modo_rotulos=modo_rotulos,
                )

        # =====================================================================
        # BLOCO 2 — KPIs OPERACIONAIS + GRÁFICOS OPERACIONAIS SEPARADOS
        # =====================================================================
        st.markdown("---")
        st.markdown(f"### 🏭 Bloco Operacional Projetado (Produção & Expedição) — {periodo_str}")

        tot_notas_prev = float(np.sum(prev_notas["forecast"]))
        tot_saud_prev = float(np.sum(prev_saudavel["forecast"]))
        tot_back_prev = float(np.sum(prev_backlog["forecast"]))
        tot_exp_prev = float(np.sum(prev_exp["forecast"]))
        tot_skus_prev = float(np.sum(prev_skus["forecast"]))

        kp1, kp2, kp3, kp4, kp5 = st.columns(5)
        kp1.metric(
            "📦 Notas Realizadas Previstas",
            _fmt_int(tot_notas_prev),
            delta=_delta_pct_str(tot_notas_prev / n_dias_prev, _calc_media_benchmark(df_prod_hist, "Notas_Realizadas")),
        )
        kp2.metric(
            "🟢 Notas Saudáveis Previstas",
            _fmt_int(tot_saud_prev),
            delta=_delta_pct_str(tot_saud_prev / n_dias_prev, _calc_media_benchmark(df_prod_hist, "Saudavel")),
        )
        kp3.metric(
            "🔴 Backlog Previsto",
            _fmt_int(tot_back_prev),
            delta=_delta_pct_str(tot_back_prev / n_dias_prev, _calc_media_benchmark(df_prod_hist, "Backlog")),
            delta_color="inverse",
        )
        kp4.metric(
            "🚚 Volume Expedido Previsto",
            _fmt_int(tot_exp_prev),
            delta=_delta_pct_str(tot_exp_prev / n_dias_prev, _calc_media_benchmark(df_prod_hist, "Total_Expedidos")),
        )
        kp5.metric(
            "🏷️ SKUs Separados Previstos",
            _fmt_int(tot_skus_prev),
            delta=_delta_pct_str(tot_skus_prev / n_dias_prev, _calc_media_benchmark(df_prod_hist, "Total_SKUs")),
        )

        if n_dias_prev > 10:
            _plot_somente_previsao_multi(
                f"📦 Previsão Diária: Notas Realizadas, Saudáveis & Backlog ({modelo_sel})",
                datas_alvo,
                [
                    {"nome": "Notas Realizadas", "valores": prev_notas["forecast"], "cor": "#1f77b4", "tipo": "barra"},
                    {"nome": "Notas Saudáveis", "valores": prev_saudavel["forecast"], "cor": "#16a34a", "tipo": "linha"},
                    {
                        "nome": "Backlog (Eixo Dir.)",
                        "valores": prev_backlog["forecast"],
                        "cor": "#dc2626",
                        "tipo": "linha",
                        "dash": "dash",
                        "eixo_secundario": True,
                    },
                ],
                is_moeda=False,
                altura=440,
                modo_rotulos=modo_rotulos,
            )
            _plot_somente_previsao_multi(
                f"🚚 Previsão Diária: Volume Expedido & SKUs ({modelo_sel})",
                datas_alvo,
                [
                    {"nome": "Volume Expedido", "valores": prev_exp["forecast"], "cor": "#ea580c", "tipo": "barra"},
                    {"nome": "SKUs Separados", "valores": prev_skus["forecast"], "cor": "#0284c7", "tipo": "linha"},
                ],
                is_moeda=False,
                altura=420,
                modo_rotulos=modo_rotulos,
            )
        else:
            col_op1, col_op2 = st.columns(2)
            with col_op1:
                _plot_somente_previsao_multi(
                    f"📦 Previsão Diária: Notas Realizadas, Saudáveis & Backlog ({modelo_sel})",
                    datas_alvo,
                    [
                        {"nome": "Notas Realizadas", "valores": prev_notas["forecast"], "cor": "#1f77b4", "tipo": "barra"},
                        {"nome": "Notas Saudáveis", "valores": prev_saudavel["forecast"], "cor": "#16a34a", "tipo": "linha"},
                        {
                            "nome": "Backlog (Eixo Dir.)",
                            "valores": prev_backlog["forecast"],
                            "cor": "#dc2626",
                            "tipo": "linha",
                            "dash": "dash",
                            "eixo_secundario": True,
                        },
                    ],
                    is_moeda=False,
                    altura=440,
                    modo_rotulos=modo_rotulos,
                )

            with col_op2:
                _plot_somente_previsao_multi(
                    f"🚚 Previsão Diária: Volume Expedido & SKUs ({modelo_sel})",
                    datas_alvo,
                    [
                        {"nome": "Volume Expedido", "valores": prev_exp["forecast"], "cor": "#ea580c", "tipo": "barra"},
                        {"nome": "SKUs Separados", "valores": prev_skus["forecast"], "cor": "#0284c7", "tipo": "linha"},
                    ],
                    is_moeda=False,
                    altura=440,
                    modo_rotulos=modo_rotulos,
                )

        # =====================================================================
        # TABELA CONSOLIDADA DIÁRIA DAS PREVISÕES
        # =====================================================================
        st.markdown("---")
        st.markdown(f"### 📋 Cronograma Diário Projetado ({periodo_str})")

        dias_pt = {0: "Segunda", 1: "Terça", 2: "Quarta", 3: "Quinta", 4: "Sexta", 5: "Sábado"}
        df_prev_tabela = pd.DataFrame(
            {
                "Data Projetada": datas_alvo.strftime("%d/%m/%Y"),
                "Dia da Semana": datas_alvo.dayofweek.map(dias_pt),
                "Fat. Bruto Previsto": [_fmt_brl(v) for v in prev_fat_bruto_vals],
                "Devoluções Previstas": [_fmt_brl(-v) for v in prev_dev["forecast"]],
                "Fat. Líquido Previsto": [_fmt_brl(v) for v in prev_fat_liq["forecast"]],
                "Notas Previstas": [_fmt_int(v) for v in prev_notas["forecast"]],
                "Saudáveis Previstas": [_fmt_int(v) for v in prev_saudavel["forecast"]],
                "Backlog Previsto": [_fmt_int(v) for v in prev_backlog["forecast"]],
                "Expedição Prevista": [_fmt_int(v) for v in prev_exp["forecast"]],
                "SKUs Previstos": [_fmt_int(v) for v in prev_skus["forecast"]],
                "Custo Frete Previsto": [_fmt_brl(v) for v in prev_frete["forecast"]],
            }
        )
        st.dataframe(df_prev_tabela, use_container_width=True, height=380, hide_index=True)

        csv_prev = df_prev_tabela.to_csv(index=False, sep=";").encode("utf-8-sig")
        st.download_button(
            label="📥 Baixar Previsões Projetadas (CSV)",
            data=csv_prev,
            file_name=f"Previsoes_BI_{n_dias_prev}_dias.csv",
            mime="text/csv",
        )

        # =====================================================================
        # COMPARATIVO MENSAL CONSOLIDADO DAS PROJEÇÕES
        # =====================================================================
        st.markdown("---")
        st.markdown(f"### 📅 Comparativo Mensal Consolidado das Projeções ({modelo_sel})")

        df_prev_mes_raw = pd.DataFrame(
            {
                "Mes_Ano": datas_alvo.strftime("%Y-%m"),
                "Fat_Bruto": prev_fat_bruto_vals,
                "Fat_Liq": prev_fat_liq["forecast"],
                "Devolucoes": prev_dev["forecast"],
                "Frete": prev_frete["forecast"],
                "Notas": prev_notas["forecast"],
                "Saudavel": prev_saudavel["forecast"],
                "Backlog": prev_backlog["forecast"],
                "Expedidos": prev_exp["forecast"],
            }
        )
        df_prev_mes = df_prev_mes_raw.groupby("Mes_Ano", as_index=False).sum().sort_values("Mes_Ano").reset_index(drop=True)

        col_pm1, col_pm2 = st.columns(2)
        with col_pm1:
            st.markdown("#### 💰 Projeção Mensal: Faturamento Bruto, Líquido & Frete (R$)")
            fig_pm_fin = go.Figure()
            fig_pm_fin.add_trace(
                go.Bar(
                    x=df_prev_mes["Mes_Ano"],
                    y=df_prev_mes["Fat_Bruto"],
                    name="Fat. Bruto Previsto",
                    marker_color="#1f77b4",
                    text=[_fmt_brl_compacto(v) for v in df_prev_mes["Fat_Bruto"]],
                    textposition="outside",
                    cliponaxis=False,
                )
            )
            fig_pm_fin.add_trace(
                go.Bar(
                    x=df_prev_mes["Mes_Ano"],
                    y=df_prev_mes["Fat_Liq"],
                    name="Fat. Líquido Previsto",
                    marker_color="#16a34a",
                    text=[_fmt_brl_compacto(v) for v in df_prev_mes["Fat_Liq"]],
                    textposition="outside",
                    cliponaxis=False,
                )
            )
            fig_pm_fin.add_trace(
                go.Bar(
                    x=df_prev_mes["Mes_Ano"],
                    y=df_prev_mes["Frete"],
                    name="Frete Previsto",
                    marker_color="#7c3aed",
                    text=[_fmt_brl_compacto(v) for v in df_prev_mes["Frete"]],
                    textposition="outside",
                    cliponaxis=False,
                )
            )
            max_pmf = max(float(df_prev_mes["Fat_Bruto"].max()), 100.0)
            fig_pm_fin.update_layout(
                template="plotly_white",
                height=420,
                barmode="group",
                margin=dict(l=40, r=25, t=45, b=45),
                xaxis=dict(type="category"),
                yaxis=dict(title="<b>Valor Mensal Projetado (R$)</b>", range=[0, max_pmf * 1.28], gridcolor="#e9ecef"),
                legend=dict(orientation="h", y=1.14, x=0, xanchor="left"),
            )
            st.plotly_chart(fig_pm_fin, use_container_width=True)

        with col_pm2:
            st.markdown("#### 🏭 Projeção Mensal: Notas Realizadas, Saudáveis, Backlog & Expedição")
            fig_pm_op = go.Figure()
            for col_k, nome_k, cor_k in [
                ("Notas", "Notas Realizadas", "#1f77b4"),
                ("Saudavel", "Notas Saudáveis", "#16a34a"),
                ("Backlog", "Backlog", "#dc2626"),
                ("Expedidos", "Volume Expedido", "#ea580c"),
            ]:
                fig_pm_op.add_trace(
                    go.Bar(
                        x=df_prev_mes["Mes_Ano"],
                        y=df_prev_mes[col_k],
                        name=nome_k,
                        marker_color=cor_k,
                        text=[_fmt_int(v) for v in df_prev_mes[col_k]],
                        textposition="outside",
                        cliponaxis=False,
                    )
                )
            max_pmo = max(float(df_prev_mes[["Notas", "Saudavel", "Backlog", "Expedidos"]].max().max()), 10.0)
            fig_pm_op.update_layout(
                template="plotly_white",
                height=420,
                barmode="group",
                margin=dict(l=40, r=25, t=45, b=45),
                xaxis=dict(type="category"),
                yaxis=dict(title="<b>Volume Mensal Projetado</b>", range=[0, max_pmo * 1.28], gridcolor="#e9ecef"),
                legend=dict(orientation="h", y=1.14, x=0, xanchor="left"),
            )
            st.plotly_chart(fig_pm_op, use_container_width=True)


def render_secao_previsao_vs_real(df_diario: pd.DataFrame):
    """
    Aba 'Comparação de Previsão X Real': união entre Previsão e Realizado
    por Semana, Mês ou Calendário Específico, mostrando em quais dias o Real
    superou a Previsão e vice-versa sem sobreposição de rótulos.
    """
    st.markdown("## ⚖️ Comparação de Previsão X Real — Aderência & Superação de Metas")
    st.caption(
        "União direta entre o Realizado e a Previsão estatística na semana, mês ou dias selecionados no calendário, "
        "destacando os dias em que o Real superou a Previsão e vice-versa."
    )

    if df_diario is None or df_diario.empty:
        st.info("Aguardando carregamento de dados para comparação.")
        return

    df = df_diario.copy()
    df["DATA"] = pd.to_datetime(df["DATA"], errors="coerce").dt.normalize()
    df = df.dropna(subset=["DATA"]).sort_values("DATA").reset_index(drop=True)
    df = df[df["DATA"].dt.strftime("%d/%m") != "02/01"].reset_index(drop=True)

    if len(df) < 10:
        st.warning("Histórico mínimo de 10 dias necessário para validação cruzada Previsão X Real.")
        return

    col_fat_bruto = "Todas as Unidades (Geral)_Fat"
    col_fat_liq = (
        "Todas as Unidades (Geral)_Liq"
        if "Todas as Unidades (Geral)_Liq" in df.columns
        else "Todas as Unidades (Geral)_Fat"
    )
    df["Fat_Liq_Real"] = df[col_fat_liq]
    df["Fat_Bruto_Real"] = (
        df[col_fat_bruto]
        if "Todas as Unidades (Geral)_Liq" in df.columns
        else df[col_fat_bruto] + df["Todas as Unidades (Geral)_Dev"].abs()
    )

    # =========================================================================
    # CONTROLES DA COMPARAÇÃO (PERÍODO & MODELO)
    # =========================================================================
    c1, c2, c3 = st.columns([1.2, 1.5, 1.3])

    with c1:
        tipo_filtro = st.radio(
            "Filtrar período por:",
            ["Por Semana", "Por Mês", "Calendário Específico"],
            horizontal=True,
            key="pvr_tipo_filtro",
        )

    min_dt = df["DATA"].min().date()
    max_dt = df["DATA"].max().date()

    with c2:
        if tipo_filtro == "Por Semana":
            df["Sem_Ini"] = df["DATA"].apply(lambda d: d - pd.Timedelta(days=d.weekday()))
            df["Sem_Fim"] = df["Sem_Ini"] + pd.Timedelta(days=6)
            df["Sem_Label"] = (
                "Semana " + df["Sem_Ini"].dt.strftime("%d/%m") + " a " + df["Sem_Fim"].dt.strftime("%d/%m")
            )
            semanas_ord = df.sort_values("Sem_Ini")["Sem_Label"].unique().tolist()
            sem_sel = st.selectbox("Selecione a Semana:", semanas_ord, index=len(semanas_ord) - 1, key="pvr_sem_sel")
            dt_ini = df[df["Sem_Label"] == sem_sel]["DATA"].min()
            dt_fim = df[df["Sem_Label"] == sem_sel]["DATA"].max()
        elif tipo_filtro == "Por Mês":
            df["Mes_Ano"] = df["DATA"].dt.strftime("%Y-%m")
            meses_ord = sorted(df["Mes_Ano"].unique().tolist())
            mes_sel = st.selectbox("Selecione o Mês:", meses_ord, index=len(meses_ord) - 1, key="pvr_mes_sel")
            dt_ini = df[df["Mes_Ano"] == mes_sel]["DATA"].min()
            dt_fim = df[df["Mes_Ano"] == mes_sel]["DATA"].max()
        else:
            default_ini = max(min_dt, (max_dt - pd.Timedelta(days=14)))
            dts = st.date_input(
                "Selecione o intervalo de dias:",
                value=(default_ini, max_dt),
                min_value=min_dt,
                max_value=max_dt,
                key="pvr_cal_sel",
            )
            if isinstance(dts, tuple) and len(dts) == 2:
                dt_ini, dt_fim = pd.Timestamp(dts[0]), pd.Timestamp(dts[1])
            else:
                dt_ini, dt_fim = pd.Timestamp(default_ini), pd.Timestamp(max_dt)

    with c3:
        modelo_pvr = st.selectbox(
            "🧠 Modelo de Previsão de Referência:",
            [
                "Ensemble Ponderado (Média DS)",
                "Regressão Linear (OLS)",
                "Ridge + Sazonalidade Semanal",
                "Polinomial Grau 2 (Amortecido)",
                "Suavização Exponencial (Holt)",
            ],
            index=0,
            key="pvr_modelo_sel",
        )

    df_periodo = df[(df["DATA"] >= dt_ini) & (df["DATA"] <= dt_fim)].copy().reset_index(drop=True)
    if df_periodo.empty:
        st.warning("Nenhum dado encontrado para o período selecionado.")
        return

    df_treino = df[df["DATA"] < dt_ini].copy().reset_index(drop=True)
    if len(df_treino) < 6:
        df_treino = df.copy().reset_index(drop=True)

    datas_alvo = pd.DatetimeIndex(df_periodo["DATA"])

    def _prever_col(col_nome: str) -> np.ndarray:
        sub_tr = df_treino[df_treino[col_nome] > 0] if (df_treino[col_nome] > 0).sum() >= 4 else df_treino
        res = _treinar_e_prever_datas(
            pd.DatetimeIndex(sub_tr["DATA"]),
            sub_tr[col_nome].values,
            datas_alvo,
            modelo_pvr,
        )
        return res["forecast"]

    df_periodo["Prev_Fat_Liq"] = _prever_col("Fat_Liq_Real")
    df_periodo["Prev_Notas"] = _prever_col("Notas_Realizadas")
    df_periodo["Prev_Expedidos"] = _prever_col("Total_Expedidos")
    df_periodo["Prev_Frete"] = _prever_col("Total_Frete")
    df_periodo["Prev_Backlog"] = _prever_col("Backlog")

    # =========================================================================
    # SELETOR DO INDICADOR PARA ANÁLISE DETALHADA PREVISÃO X REAL
    # =========================================================================
    st.markdown("---")
    indicador_sel = st.selectbox(
        "🎯 Selecione o Indicador (Todos os Gráficos Anteriores Disponíveis):",
        [
            "💵 Faturamento Líquido (R$)",
            "📦 Notas Realizadas / PVs (Qtd)",
            "🚚 Volume Expedido (Qtd)",
            "💸 Custo de Frete Terceirizado (R$)",
            "🔴 Backlog Operacional (Qtd)",
        ],
        index=0,
        key="pvr_indicador_sel",
    )

    mapa_ind = {
        "💵 Faturamento Líquido (R$)": ("Fat_Liq_Real", "Prev_Fat_Liq", True, False),
        "📦 Notas Realizadas / PVs (Qtd)": ("Notas_Realizadas", "Prev_Notas", False, False),
        "🚚 Volume Expedido (Qtd)": ("Total_Expedidos", "Prev_Expedidos", False, False),
        "💸 Custo de Frete Terceirizado (R$)": ("Total_Frete", "Prev_Frete", True, True),
        "🔴 Backlog Operacional (Qtd)": ("Backlog", "Prev_Backlog", False, True),
    }

    col_real, col_prev, is_moeda, menor_eh_melhor = mapa_ind[indicador_sel]
    real_vals = df_periodo[col_real].values.astype(float)
    prev_vals = df_periodo[col_prev].values.astype(float)
    diff_vals = real_vals - prev_vals

    tot_real = float(np.sum(real_vals))
    tot_prev = float(np.sum(prev_vals))
    saldo_tot = tot_real - tot_prev
    var_pct = ((tot_real - tot_prev) / tot_prev * 100) if tot_prev > 0 else 0.0

    dias_real_maior = int(np.sum(real_vals > prev_vals))
    dias_prev_maior = int(np.sum(prev_vals > real_vals))
    dias_empate = int(np.sum(np.isclose(real_vals, prev_vals)))

    mape = float(np.mean(np.abs(diff_vals) / np.maximum(np.maximum(real_vals, prev_vals), 1.0)) * 100)
    acuracia_pct = max(0.0, 100.0 - mape)

    fmt_fn = _fmt_brl if is_moeda else _fmt_int

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("📌 Total Realizado", fmt_fn(tot_real))
    k2.metric("🔮 Total Previsto (DS)", fmt_fn(tot_prev))
    k3.metric(
        "⚖️ Saldo (Real - Previsto)",
        fmt_fn(saldo_tot),
        delta=f"{'+' if var_pct >= 0 else ''}{var_pct:.1f}%",
        delta_color="inverse" if menor_eh_melhor else "normal",
    )
    k4.metric("🏆 Dias Real > Previsto", f"{dias_real_maior} dia(s)", delta=f"De {len(df_periodo)} dias analisados", delta_color="off")
    k5.metric("📉 Dias Previsto > Real", f"{dias_prev_maior} dia(s)", delta=f"Aderência Média: {acuracia_pct:.1f}%", delta_color="off")

    dias_sem = {0: "Seg", 1: "Ter", 2: "Qua", 3: "Qui", 4: "Sex", 5: "Sáb", 6: "Dom"}
    x_labels = [f"{d.strftime('%d/%m')} ({dias_sem[d.weekday()]})" for d in df_periodo["DATA"]]
    fmt_hover = "R$ %{y:,.2f}" if is_moeda else "%{y:,.1f}"

    # =========================================================================
    # GRÁFICO 1: UNIÃO PREVISÃO X REAL (ANTI-SOBREPOSIÇÃO: BARRA INSIDE + LINHA TOP)
    # =========================================================================
    st.markdown(f"#### 📊 Gráfico 1 — União Previsão X Real: {indicador_sel}")
    fig_uniao = go.Figure()

    n_pvr = len(x_labels)
    passo_pvr = 1 if n_pvr <= 12 else 2

    txt_real = [
        (_fmt_brl_compacto(v) if is_moeda else _fmt_int(v)) if (i % passo_pvr == 0 or i == n_pvr - 1) else ""
        for i, v in enumerate(real_vals)
    ]
    txt_prev = [
        (_fmt_brl_compacto(v) if is_moeda else _fmt_int(v)) if (i % passo_pvr == 0 or i == n_pvr - 1) else ""
        for i, v in enumerate(prev_vals)
    ]

    fig_uniao.add_trace(
        go.Bar(
            x=x_labels,
            y=real_vals,
            name="Realizado",
            marker_color="#1f77b4",
            opacity=0.86,
            text=txt_real,
            textposition="inside",
            insidetextanchor="middle",
            textfont=dict(size=11, color="#ffffff", family="Arial Black"),
            cliponaxis=False,
            hovertemplate=f"<b>%{{x}}</b><br>Realizado: {fmt_hover}<extra></extra>",
        )
    )

    fig_uniao.add_trace(
        go.Scatter(
            x=x_labels,
            y=prev_vals,
            mode="lines+markers+text",
            name=f"Previsão ({modelo_pvr})",
            line=dict(color="#d97706", width=3.2, dash="dash"),
            marker=dict(size=9, symbol="diamond"),
            text=txt_prev,
            textposition="top center",
            textfont=dict(size=10, color="#b45309", family="Arial Black"),
            cliponaxis=False,
            hovertemplate=f"<b>%{{x}}</b><br>Previsto: {fmt_hover}<extra></extra>",
        )
    )

    max_u = max(float(np.max(real_vals)), float(np.max(prev_vals)), 10.0)
    fig_uniao.update_layout(
        template="plotly_white",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#000000", size=11, family="Arial"),
        height=440,
        margin=dict(l=45, r=35, t=45, b=65),
        hovermode="x unified",
        xaxis=dict(type="category", tickangle=-35, tickfont=dict(size=10, color="#000000")),
        yaxis=dict(
            title=dict(text="<b>Valor (R$)</b>" if is_moeda else "<b>Volume</b>", font=dict(size=12, color="#000000")),
            showgrid=True,
            gridcolor="#e9ecef",
            range=[0, max_u * 1.26],
        ),
        legend=dict(orientation="h", y=1.14, x=0.0, xanchor="left", font=dict(size=11, color="#000000")),
    )
    st.plotly_chart(fig_uniao, use_container_width=True)

    # =========================================================================
    # GRÁFICO 2: SALDO DIÁRIO (DIAS EM QUE O REAL SUPEROU A PREVISÃO E VICE-VERSA)
    # =========================================================================
    col_d1, col_d2 = st.columns([1.65, 1.0])

    with col_d1:
        st.markdown("#### 🎯 Gráfico 2 — Diferença Diária (Real − Previsão): Quem Superou Quem?")
        cores_diff = [
            ("#dc2626" if menor_eh_melhor else "#16a34a") if d >= 0 else ("#16a34a" if menor_eh_melhor else "#dc2626")
            for d in diff_vals
        ]
        fig_diff = go.Figure(
            go.Bar(
                x=x_labels,
                y=diff_vals,
                marker_color=cores_diff,
                text=[
                    f"{'+' if d >= 0 else ''}{_fmt_brl_compacto(d) if is_moeda else _fmt_int(d)}"
                    if (i % passo_pvr == 0 or i == n_pvr - 1)
                    else ""
                    for i, d in enumerate(diff_vals)
                ],
                textposition="outside",
                textfont=dict(size=10, color="#000000", family="Arial Black"),
                cliponaxis=False,
                hovertemplate=f"<b>%{{x}}</b><br>Diferença (Real - Previsto): {fmt_hover}<extra></extra>",
            )
        )
        fig_diff.add_hline(y=0, line_width=1.8, line_color="#334155")
        max_abs_d = max(float(np.max(np.abs(diff_vals))), 10.0)
        fig_diff.update_layout(
            template="plotly_white",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#000000", size=11, family="Arial"),
            height=400,
            margin=dict(l=45, r=35, t=35, b=65),
            xaxis=dict(type="category", tickangle=-35, tickfont=dict(size=10, color="#000000")),
            yaxis=dict(
                title=dict(text="<b>Diferença (Real − Previsto)</b>", font=dict(size=12, color="#000000")),
                showgrid=True,
                gridcolor="#e9ecef",
                range=[-max_abs_d * 1.35, max_abs_d * 1.35],
            ),
        )
        st.plotly_chart(fig_diff, use_container_width=True)

    with col_d2:
        st.markdown("#### 🏅 Placar de Superação por Dia")
        fig_pizza = go.Figure(
            go.Pie(
                labels=["Real Superou Previsão", "Previsão Superou Real", "Empate Exato"],
                values=[dias_real_maior, dias_prev_maior, dias_empate],
                hole=0.45,
                marker_colors=["#16a34a", "#dc2626", "#94a3b8"],
                textinfo="label+value+percent",
                textfont=dict(size=11, color="#000000"),
            )
        )
        fig_pizza.update_layout(
            template="plotly_white",
            height=400,
            margin=dict(l=15, r=15, t=35, b=25),
            showlegend=False,
        )
        st.plotly_chart(fig_pizza, use_container_width=True)

    # =========================================================================
    # TABELA DETALHADA DIA A DIA: PREVISÃO X REAL (TODOS OS INDICADORES)
    # =========================================================================
    st.markdown("---")
    st.markdown("### 📋 Auditoria Diária Completa — Previsão X Real (Todos os Gráficos)")

    status_list = []
    for r, p in zip(real_vals, prev_vals):
        if r > p:
            status_list.append("🟢 Real Superou Previsão")
        elif p > r:
            status_list.append("🔴 Previsão Superou Real")
        else:
            status_list.append("⚪ Empate")

    df_auditoria = pd.DataFrame(
        {
            "Data": df_periodo["DATA"].dt.strftime("%d/%m/%Y"),
            "Dia": df_periodo["DATA"].dt.dayofweek.map({0: "Seg", 1: "Ter", 2: "Qua", 3: "Qui", 4: "Sex", 5: "Sáb"}),
            "Resultado (Indicador Sel.)": status_list,
            "Fat. Líq. Real": [_fmt_brl(v) for v in df_periodo["Fat_Liq_Real"]],
            "Fat. Líq. Previsto": [_fmt_brl(v) for v in df_periodo["Prev_Fat_Liq"]],
            "Notas Real": [_fmt_int(v) for v in df_periodo["Notas_Realizadas"]],
            "Notas Previstas": [_fmt_int(v) for v in df_periodo["Prev_Notas"]],
            "Expedidos Real": [_fmt_int(v) for v in df_periodo["Total_Expedidos"]],
            "Expedidos Previstos": [_fmt_int(v) for v in df_periodo["Prev_Expedidos"]],
            "Frete Real": [_fmt_brl(v) for v in df_periodo["Total_Frete"]],
            "Frete Previsto": [_fmt_brl(v) for v in df_periodo["Prev_Frete"]],
        }
    )
    st.dataframe(df_auditoria, use_container_width=True, height=390, hide_index=True)

    # =========================================================================
    # COMPARATIVO MENSAL CONSOLIDADO: PREVISÃO X REAL (TODOS OS INDICADORES)
    # =========================================================================
    st.markdown("---")
    st.markdown(f"### 📅 Comparativo Mensal Consolidado: Previsão X Real — {indicador_sel}")

    df_m_full = df.copy()
    datas_all = pd.DatetimeIndex(df_m_full["DATA"])
    for c_src, c_dst in [
        ("Fat_Liq_Real", "Prev_M_Fat"),
        ("Notas_Realizadas", "Prev_M_Notas"),
        ("Total_Expedidos", "Prev_M_Exp"),
        ("Total_Frete", "Prev_M_Frete"),
        ("Backlog", "Prev_M_Backlog"),
    ]:
        sub_tr_m = df_m_full[df_m_full[c_src] > 0] if (df_m_full[c_src] > 0).sum() >= 4 else df_m_full
        res_m = _treinar_e_prever_datas(
            pd.DatetimeIndex(sub_tr_m["DATA"]),
            sub_tr_m[c_src].values,
            datas_all,
            modelo_pvr,
        )
        df_m_full[c_dst] = res_m["forecast"]

    df_m_full["Mes_Ano"] = df_m_full["DATA"].dt.strftime("%Y-%m")
    mapa_mensal_pvr = {
        "💵 Faturamento Líquido (R$)": ("Fat_Liq_Real", "Prev_M_Fat", True),
        "📦 Notas Realizadas / PVs (Qtd)": ("Notas_Realizadas", "Prev_M_Notas", False),
        "🚚 Volume Expedido (Qtd)": ("Total_Expedidos", "Prev_M_Exp", False),
        "💸 Custo de Frete Terceirizado (R$)": ("Total_Frete", "Prev_M_Frete", True),
        "🔴 Backlog Operacional (Qtd)": ("Backlog", "Prev_M_Backlog", False),
    }

    c_real_m, c_prev_m, is_moeda_m = mapa_mensal_pvr[indicador_sel]
    df_grp_m = (
        df_m_full.groupby("Mes_Ano", as_index=False)[[c_real_m, c_prev_m]]
        .sum()
        .sort_values("Mes_Ano")
        .reset_index(drop=True)
    )
    df_grp_m = df_grp_m[(df_grp_m[c_real_m] > 0) | (df_grp_m[c_prev_m] > 0)].reset_index(drop=True)

    if not df_grp_m.empty:
        fig_pvr_m = go.Figure()
        fig_pvr_m.add_trace(
            go.Bar(
                x=df_grp_m["Mes_Ano"],
                y=df_grp_m[c_real_m],
                name="Total Mensal Realizado",
                marker_color="#1f77b4",
                text=[_fmt_brl(v) if is_moeda_m else _fmt_int(v) for v in df_grp_m[c_real_m]],
                textposition="outside",
                textfont=dict(size=10, color="#000000", family="Arial Black"),
                cliponaxis=False,
            )
        )
        fig_pvr_m.add_trace(
            go.Bar(
                x=df_grp_m["Mes_Ano"],
                y=df_grp_m[c_prev_m],
                name=f"Total Mensal Previsto ({modelo_pvr})",
                marker_color="#d97706",
                text=[_fmt_brl(v) if is_moeda_m else _fmt_int(v) for v in df_grp_m[c_prev_m]],
                textposition="outside",
                textfont=dict(size=10, color="#b45309", family="Arial Black"),
                cliponaxis=False,
            )
        )
        max_pm_pvr = max(float(df_grp_m[c_real_m].max()), float(df_grp_m[c_prev_m].max()), 10.0)
        fig_pvr_m.update_layout(
            template="plotly_white",
            height=440,
            barmode="group",
            bargap=0.25,
            margin=dict(l=45, r=30, t=45, b=45),
            xaxis=dict(type="category"),
            yaxis=dict(
                title=dict(text="<b>Total Mensal (R$)</b>" if is_moeda_m else "<b>Total Mensal (Qtd)</b>"),
                range=[0, max_pm_pvr * 1.26],
                gridcolor="#e9ecef",
            ),
            legend=dict(orientation="h", y=1.14, x=0, xanchor="left"),
        )
        st.plotly_chart(fig_pvr_m, use_container_width=True)