# pages/1_📊_Generate_Analysis.py
import streamlit as st
import pandas as pd
from src.cloud_io import MongoIO
from src.constants import SESSION_PRODUCT_KEY
from src.data_report.generate_data_report import DashboardGenerator

mongo_con = MongoIO()

def create_analysis_page():
    try:
        if "data" in st.session_state and st.session_state["data"]:
            product_name = st.session_state.get(SESSION_PRODUCT_KEY)
            if product_name:
                data = mongo_con.get_reviews(product_name=product_name)
                if data is None or data.empty:
                    st.warning("⚠️ No data found for this product. Please scrape first.")
                else:
                    dashboard = DashboardGenerator(data)
                    dashboard.display_general_info()
                    dashboard.display_product_sections()
            else:
                st.warning("❌ No product selected. Go to Scraper page first.")
        else:
            st.info("ℹ️ Please scrape data first using the main Scraper page.")
    except Exception as e:
        st.error(f"Analysis error: {e}")

create_analysis_page()
