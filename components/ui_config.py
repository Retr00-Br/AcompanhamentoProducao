import streamlit as st


class DashboardUI:
    def __init__(self):
        self.title = "📊 Painel Operacional & BI"
        self.subtitle = "Acompanhamento de Faturamento, Produção, Expedição e Custos Logísticos"

    def render_header(self):
        st.markdown(
            f"""
            <div style="padding: 10px 0px 15px 0px; border-bottom: 2px solid #e9ecef; margin-bottom: 20px;">
                <h1 style="margin: 0; font-size: 2.0rem; color: #1f2937;">{self.title}</h1>
                <p style="margin: 4px 0 0 0; font-size: 1.0rem; color: #6b7280;">{self.subtitle}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )