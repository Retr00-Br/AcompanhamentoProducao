import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st


def _fmt_brl(val: float) -> str:
    sinal = "-" if val < 0 else ""
    return f"{sinal}R$ {abs(val):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _fmt_int(val: float) -> str:
    return f"{int(round(val)):,}".replace(",", ".")


def _gerar_proximos_dias_uteis(ultima_data: pd.Timestamp, n_dias: int) -> pd.DatetimeIndex:
    """Gera os próximos N dias operacionais (segunda a sábado, excluindo domingos)."""
    datas = []
    curr = pd.Timestamp(ultima_data) + pd.Timedelta(days=1)
    while len(datas) < n_dias:
        if curr.weekday() != 6:  # exclui apenas domingo
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
    retornando histórico ajustado, previsão futura, intervalo de confiança 95% e métricas de erro (RMSE / R2).
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
                "Regressão Linear (OLS)": fut_const,
                "Ridge + Sazonalidade Semanal": fut_const,
                "Polinomial Grau 2 (Amortecido)": fut_const,
                "Suavização Exponencial (Holt)": fut_const,
                "Ensemble Ponderado (Média DS)": fut_const,
            },
        }

    t = np.arange(n, dtype=float)
    t_fut = np.arange(n, n + h, dtype=float)

    # -------------------------------------------------------------------------
    # 1. REGRESSÃO LINEAR SIMPLES (OLS)
    # -------------------------------------------------------------------------
    b_ols, a_ols = np.polyfit(t, y, 1)
    fit_ols = a_ols + b_ols * t
    pred_ols = np.maximum(a_ols + b_ols * t_fut, 0.0)

    # -------------------------------------------------------------------------
    # 2. REGRESSÃO RIDGE (L2) COM TENDÊNCIA + SAZONALIDADE POR DIA DA SEMANA
    # -------------------------------------------------------------------------
    dows_all = list(range(6))  # Seg(0) a Sáb(5)
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
    reg[0, 0] = 0.0  # não penaliza o intercepto
    beta_ridge = np.linalg.solve(X_hist.T @ X_hist + reg, X_hist.T @ y)

    fit_ridge = X_hist @ beta_ridge
    pred_ridge = np.maximum(X_fut @ beta_ridge, 0.0)

    # -------------------------------------------------------------------------
    # 3. REGRESSÃO POLINOMIAL GRAU 2 (COM AMORTECIMENTO DE HORIZONTE)
    # -------------------------------------------------------------------------
    if n >= 6:
        c2, c1, c0 = np.polyfit(t, y, 2)
        fit_poly = c2 * (t**2) + c1 * t + c0
        # Amortecimento para evitar explosão quadrática em horizontes longos
        t_fut_damp = n + np.cumsum(0.96 ** np.arange(1, h + 1))
        pred_poly = np.maximum(c2 * (t_fut_damp**2) + c1 * t_fut_damp + c0, 0.0)
    else:
        fit_poly = fit_ols.copy()
        pred_poly = pred_ols.copy()

    # -------------------------------------------------------------------------
    # 4. SUAVIZAÇÃO EXPONENCIAL DUPLA (HOLT'S LINEAR TREND)
    # -------------------------------------------------------------------------
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

    # -------------------------------------------------------------------------
    # 5. ENSEMBLE PONDERADO (MÉDIA DOS MODELOS DE REGRESSÃO E SÉRIES)
    # -------------------------------------------------------------------------
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

    # Intervalo de confiança de 95% expandindo suavemente com o horizonte
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
):
    fig = go.Figure()

    x_hist_str = datas_hist.strftime("%d/%m").tolist()
    x_fut_str = datas_fut.strftime("%d/%m").tolist()

    fmt_hover = "R$ %{y:,.2f}" if is_moeda else "%{y:,.1f}"

    # Banda de Confiança 95%
    fig.add_trace(
        go.Scatter(
            x=x_fut_str + x_fut_str[::-1],
            y=list(res_modelo["upper_95"]) + list(res_modelo["lower_95"][::-1]),
            fill="toself",
            fillcolor="rgba(217, 119, 6, 0.14)",
            line=dict(color="rgba(255,255,255,0)"),
            hoverinfo="skip",
            showlegend=True,
            name="Intervalo de Confiança (95%)",
        )
    )

    # Histórico Real
    fig.add_trace(
        go.Scatter(
            x=x_hist_str,
            y=valores_hist,
            mode="lines+markers",
            name="Histórico Real",
            line=dict(color=cor_hist, width=2.2),
            marker=dict(size=6),
            hovertemplate=f"<b>Data: %{{x}}</b><br>Real: {fmt_hover}<extra></extra>",
        )
    )

    # Linha de Tendência Histórica (Ajuste do Modelo)
    fig.add_trace(
        go.Scatter(
            x=x_hist_str,
            y=res_modelo["hist_fit"],
            mode="lines",
            name="Tendência Ajustada (Modelo)",
            line=dict(color="#6c757d", width=1.8, dash="dot"),
            hovertemplate=f"<b>Data: %{{x}}</b><br>Ajuste Modelo: {fmt_hover}<extra></extra>",
        )
    )

    # Previsão Futura conectada ao último ponto real
    x_conn = [x_hist_str[-1]] + x_fut_str
    y_conn = [float(valores_hist[-1])] + list(res_modelo["forecast"])

    fig.add_trace(
        go.Scatter(
            x=x_conn,
            y=y_conn,
            mode="lines+markers+text",
            name="Previsão Futura (DS)",
            line=dict(color=cor_prev, width=3.0, dash="dash"),
            marker=dict(size=8, symbol="diamond"),
            text=[""] + [
                (_fmt_brl(v) if is_moeda else _fmt_int(v)) if (i % max(len(x_fut_str) // 8, 1) == 0) else ""
                for i, v in enumerate(res_modelo["forecast"])
            ],
            textposition="top center",
            textfont=dict(size=9, color=cor_prev, family="Arial Black"),
            cliponaxis=False,
            hovertemplate=f"<b>Previsão: %{{x}}</b><br>Projetado: {fmt_hover}<extra></extra>",
        )
    )

    max_y = max(
        float(np.max(valores_hist)) if len(valores_hist) > 0 else 10.0,
        float(np.max(res_modelo["upper_95"])) if len(res_modelo["upper_95"]) > 0 else 10.0,
        10.0,
    )

    fig.update_layout(
        title=dict(text=f"<b>{titulo}</b>", font=dict(size=15, color="#000000")),
        template="plotly_white",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#000000", size=12, family="Arial"),
        height=440,
        margin=dict(l=50, r=40, t=60, b=50),
        hovermode="x unified",
        xaxis=dict(type="category", tickangle=-35, tickfont=dict(size=10, color="#000000")),
        yaxis=dict(
            title=dict(text="<b>Valor Projetado (R$)</b>" if is_moeda else "<b>Volume Projetado</b>", font=dict(size=12, color="#000000")),
            showgrid=True,
            gridcolor="#e9ecef",
            range=[0, max_y * 1.22],
        ),
        legend=dict(orientation="h", y=1.13, x=1.0, xanchor="right", font=dict(size=11, color="#000000")),
    )

    st.plotly_chart(fig, use_container_width=True)


def render_secao_previsao_ds(df_diario: pd.DataFrame, df_frete_tratado: pd.DataFrame = None):
    st.markdown("## 🔮 Previsão & Data Science — Projeções Estatísticas e Regressão")
    st.caption(
        "Modelos preditivos (Regressão Linear OLS, Ridge com Sazonalidade Semanal, Polinomial Amortecido e Suavização Exponencial de Holt) "
        "aplicados sobre todo o histórico operacional para projetar KPIs e curvas futuras."
    )

    if df_diario is None or df_diario.empty:
        st.info("Aguardando carregamento de dados históricos para gerar previsões.")
        return

    df = df_diario.copy()
    df["DATA"] = pd.to_datetime(df["DATA"], errors="coerce").dt.normalize()
    df = df.dropna(subset=["DATA"]).sort_values("DATA").reset_index(drop=True)
    df = df[df["DATA"].dt.strftime("%d/%m") != "02/01"].reset_index(drop=True)

    # =========================================================================
    # CONTROLES DO MODELO DE DATA SCIENCE
    # =========================================================================
    col_c1, col_c2, col_c3 = st.columns([1.3, 1.3, 1.4])

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

    # =========================================================================
    # PREPARAÇÃO DAS SÉRIES HISTÓRICAS POR DOMÍNIO
    # =========================================================================
    col_fat_bruto = "Todas as Unidades (Geral)_Fat"
    col_fat_liq = (
        "Todas as Unidades (Geral)_Liq"
        if "Todas as Unidades (Geral)_Liq" in df.columns
        else "Todas as Unidades (Geral)_Fat"
    )
    col_dev = "Todas as Unidades (Geral)_Dev"

    # Série Faturamento (dias com movimento financeiro)
    df_fat_hist = df[(df[col_fat_bruto] > 0) | (df[col_dev].abs() > 0)].copy().reset_index(drop=True)
    if df_fat_hist.empty:
        df_fat_hist = df.copy()

    # Se _Liq não existia separado no cache antigo, garante Bruto = Liq + |Dev|
    if "Todas as Unidades (Geral)_Liq" not in df.columns:
        df_fat_hist["Fat_Liq_Real"] = df_fat_hist[col_fat_bruto]
        df_fat_hist["Fat_Bruto_Real"] = df_fat_hist[col_fat_bruto] + df_fat_hist[col_dev].abs()
    else:
        df_fat_hist["Fat_Liq_Real"] = df_fat_hist[col_fat_liq]
        df_fat_hist["Fat_Bruto_Real"] = df_fat_hist[col_fat_bruto]

    df_fat_hist["Dev_Real"] = df_fat_hist[col_dev].abs()

    # Série Produção & Expedição (a partir do início da operação real)
    mask_prod = (
        (df.get("Notas_Realizadas", 0) > 0)
        | (df.get("Saudavel", 0) > 0)
        | (df.get("Backlog", 0) > 0)
        | (df.get("Total_Expedidos", 0) > 0)
    )
    df_prod_hist = df[mask_prod].copy().reset_index(drop=True) if mask_prod.any() else df.copy()

    # Série Frete
    df_frete_hist = df[df.get("Total_Frete", 0) > 0].copy().reset_index(drop=True)
    if df_frete_hist.empty:
        df_frete_hist = df_fat_hist.copy()

    # Datas futuras de cada série
    datas_fut_fat = _gerar_proximos_dias_uteis(df_fat_hist["DATA"].max(), n_dias_prev)
    datas_fut_prod = _gerar_proximos_dias_uteis(df_prod_hist["DATA"].max(), n_dias_prev)
    datas_fut_frete = _gerar_proximos_dias_uteis(df_frete_hist["DATA"].max(), n_dias_prev)

    # Ajuste dos modelos para cada indicador
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
    # Faturamento Bruto Projetado = Líquido Projetado + Devoluções Projetadas (garantindo consistência contábil)
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

    # =========================================================================
    # FUNÇÃO AUXILIAR PARA CÁLCULO DO BENCHMARK (SEMANA, MÊS OU ACUMULADO GERAL)
    # =========================================================================
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

    # =========================================================================
    # 1. KPIs PROJETADOS — FATURAMENTO & CUSTO DE FRETE
    # =========================================================================
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

    # =========================================================================
    # 2. KPIs PROJETADOS — PRODUÇÃO & EXPEDIÇÃO
    # =========================================================================
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

    # =========================================================================
    # 3. GRÁFICOS PREDITIVOS DE FATURAMENTO & COMPARATIVO ENTRE MODELOS
    # =========================================================================
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
    )

    # Tabela Comparativa entre todos os Modelos de Regressão para Faturamento e Produção
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

    # =========================================================================
    # 4. GRÁFICOS PREDITIVOS DE PRODUÇÃO, EXPEDIÇÃO & CUSTO DE FRETE
    # =========================================================================
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
        )

    # =========================================================================
    # 5. TABELA CONSOLIDADA DIÁRIA DAS PREVISÕES & EXPORTAÇÃO CSV
    # =========================================================================
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