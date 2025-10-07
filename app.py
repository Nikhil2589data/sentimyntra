import streamlit as st
import pandas as pd
import os
from src.scrapper.scraper import ScrapeReviews
from src.cloud_io import MongoIO
from src.constants import SESSION_PRODUCT_KEY

st.set_page_config(page_title="Myntra Review Scraper", layout="wide")
st.title("🛍️ Myntra Review Scraper")

# initialize session flags
if "data" not in st.session_state:
    st.session_state["data"] = False

product_name = st.text_input("Product name (e.g., 'tshirt', 'shoes')", "")
no_of_products = st.number_input("Number of products to scrape", min_value=1, max_value=10, value=2, step=1)

# detect Streamlit Cloud environment
running_on_streamlit = os.getenv("HOME") == "/home/appuser"

if st.button("🚀 Scrape Reviews"):
    if not product_name.strip():
        st.warning("Please enter a product name.")
    else:
        with st.spinner("Scraping reviews — this may take a minute..."):
            df = None
            try:
                # disable scraper on Streamlit Cloud
                if running_on_streamlit:
                    raise Exception("⚠️ Live scraping is disabled on Streamlit Cloud. Using saved data instead.")

                # normal scraping on local system
                scraper = ScrapeReviews(product_name.strip(), int(no_of_products), headless=True, debug=False)
                df = scraper.get_review_data()
                scraper.close()

            except Exception as e:
                st.warning(str(e))
                # load fallback data if available
                try:
                    df = pd.read_csv("data/myntra_reviews_extracted.csv")
                    st.info("Loaded saved reviews from CSV instead.")
                except Exception as csv_error:
                    st.error(f"Failed to load saved CSV data: {csv_error}")
                    df = None

            # display or handle scraped/loaded data
            if df is None or df.empty:
                st.error("No reviews available. Try a different query locally or check saved CSV.")
            else:
                st.success(f"Fetched {len(df)} reviews.")
                st.dataframe(df)
                # Save to MongoDB (skip if running on Streamlit Cloud)
                if not running_on_streamlit:
                    try:
                        mongoio = MongoIO()
                        mongoio.store_reviews(product_name.strip(), df)
                        st.info("Saved reviews to MongoDB.")
                        st.session_state["data"] = True
                        st.session_state[SESSION_PRODUCT_KEY] = product_name.strip()
                    except Exception as e:
                        st.error(f"Failed to save to MongoDB: {e}")
                else:
                    st.info("MongoDB storage skipped on Streamlit Cloud.")