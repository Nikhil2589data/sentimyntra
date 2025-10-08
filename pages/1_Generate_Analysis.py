# pages/1_generate_analysis.py
import traceback
import streamlit as st
from src.cloud_io import MongoIO
from src.constants import SESSION_PRODUCT_KEY
from src.data_report.generate_data_report import DashboardGenerator

st.set_page_config(page_title="Analysis", layout="wide")

def page():
    st.title("📈 Generate Analysis")
    if "data" in st.session_state and st.session_state["data"]:
        product = st.session_state.get(SESSION_PRODUCT_KEY)
        if not product:
            st.warning("No product selected. Run the scraper first.")
            return
        # runtime DB connect inside try/except
        try:
            mongo = MongoIO()
            data = mongo.get_reviews(product_name=product)
        except Exception as e:
            st.error("Failed to connect to DB.")
            if st.checkbox("Show DB traceback (debug)"):
                st.text(traceback.format_exc())
            return

        if data is None or data.empty:
            st.info("No reviews found for this product.")
            return

        st.sidebar.markdown("### Analysis options")
        show_wordcloud = st.sidebar.checkbox("Show word cloud", value=True)
        top_kw = st.sidebar.slider("Top keywords", 5, 50, 20)
        top_reviewers = st.sidebar.slider("Top reviewers to show", 3, 20, 10)

        dashboard = DashboardGenerator(data)
        dashboard.run_all(show_wordcloud=show_wordcloud, top_n_keywords=top_kw, top_reviewers_n=top_reviewers)

    else:
        st.info("Please scrape data first from the main Scraper page.")

page()
