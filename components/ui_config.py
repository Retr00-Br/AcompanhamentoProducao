import os
import streamlit as st


class DashboardUI:

    def __init__(self):
        self.setup_css()

    def setup_css(self):
        st.markdown(
            """
            <style>
            .main { background-color: #f8f9fa; color: #000000 !important; }
            h1, h2, h3, h4, h5, h6 { color: #000000 !important; font-weight: 900 !important; }
            p, span, label, div, .stMarkdown { color: #000000 !important; font-weight: 700; font-size: 16px !important; }
            [data-testid="stMetric"] {
                background-color: #ffffff; padding: 20px; border-radius: 12px;
                border: 2px solid #adb5bd; box-shadow: 0 4px 10px rgba(0,0,0,0.1);
            }
            [data-testid="stMetricLabel"] { color: #000000 !important; font-weight: 900 !important; font-size: 17px !important; }
            [data-testid="stMetricValue"] { color: #000000 !important; font-weight: 900 !important; font-size: 30px !important; }
            .brand-logo-text { font-size: 22px; font-weight: 900; color: #0077b6; text-align: center; }
            </style>
        """,
            unsafe_allow_html=True,
        )

    def render_header(self):
        col_logo1, col_titulo, col_logo2 = st.columns([1.2, 3.6, 1.2])

        with col_logo1:
            if os.path.exists("logo_control.png"):
                st.image("logo_control.png", width=130)
            elif os.path.exists("logo.png"):
                st.image("logo.png", width=130)
            elif os.path.exists("images.jpg"):
                st.image("images.jpg", width=130)
            else:
                st.markdown('<div class="brand-logo-text">CONTROL LOG</div>', unsafe_allow_html=True)

        with col_titulo:
            st.title("Dashboard de Produção, Expedição & BI")
            st.markdown("Monitoramento e consolidação de dados via **Back-End Seguro**.")

        with col_logo2:
            if os.path.exists("logo_master.png"):
                st.image("logo_master.png", width=150)
            elif os.path.exists("master.png"):
                st.image("master.png", width=150)
            elif os.path.exists("logo2.png"):
                st.image("logo2.png", width=150)
            elif os.path.exists("higimed.png"):
                st.image("higimed.png", width=150)
            else:
                st.markdown('<div class="brand-logo-text">MASTER HIGIMED</div>', unsafe_allow_html=True)

        st.divider()