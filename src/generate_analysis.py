# src/generate_analysis.py
import traceback
import streamlit as st
import pandas as pd
from src.cloud_io import MongoIO
from src.constants import SESSION_PRODUCT_KEY
from src.data_report.generate_data_report import DashboardGenerator

def create_analysis_page(review_data: pd.DataFrame):
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
        product_key = st.session_state.get(SESSION_PRODUCT_KEY)
        if not product_key:
            st.warning("No product selected in session. Please run the scraper first.")
        else:
            try:
                mongo_con = MongoIO()
                data = mongo_con.get_reviews(product_name=product_key)
                create_analysis_page(data)
            except Exception as e:
                st.error("Failed to fetch data from MongoDB.")
                if st.checkbox("Show DB traceback (debug)"):
                    st.text(traceback.format_exc())
    else:
        st.sidebar.warning("🔍 Go to the Scraper page to collect data first.")
except Exception as e:
    st.error(f"Unexpected error: {e}")
    if st.checkbox("Show full traceback (debug)"):
        st.text(traceback.format_exc())
