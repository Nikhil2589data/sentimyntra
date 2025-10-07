# src/generate_analysis.py
import streamlit as st
import pandas as pd
from src.cloud_io import MongoIO
from src.constants import SESSION_PRODUCT_KEY
from src.data_report.generate_data_report import DashboardGenerator

mongo_con = MongoIO()

def create_analysis_page(review_data: pd.DataFrame):
    """Displays analysis dashboard once reviews are fetched"""
    if review_data is not None and not review_data.empty:
        st.dataframe(review_data)

        if st.button("📈 Generate Analysis"):
            dashboard = DashboardGenerator(review_data)
            dashboard.display_general_info()
            dashboard.display_product_sections()
    else:
        st.warning("⚠️ No data available for analysis. Please scrape data first.")

try:
    if "data" in st.session_state and st.session_state["data"]:
        data = mongo_con.get_reviews(product_name=st.session_state[SESSION_PRODUCT_KEY])
        create_analysis_page(data)
    else:
        st.sidebar.warning("🔍 Go to the Scraper page to collect data first.")
except Exception as e:
    st.error(f"Error: {e}")
