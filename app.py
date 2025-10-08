# app.py
import traceback
import streamlit as st
import pandas as pd

from src.scraper.scraper import ScrapeReviews
from src.cloud_io import MongoIO
from src.constants import SESSION_PRODUCT_KEY

st.set_page_config(page_title="Myntra Review Scraper", layout="wide")
st.title("🛍️ Myntra Review Scraper")

# initialize session flags
if "data" not in st.session_state:
    st.session_state["data"] = False

if SESSION_PRODUCT_KEY not in st.session_state:
    st.session_state[SESSION_PRODUCT_KEY] = None

# Inputs
product_name = st.text_input("Product name (e.g., 'tshirt', 'shoes')", "")
no_of_products = st.number_input(
    "Number of products to scrape", min_value=1, max_value=10, value=2, step=1
)
headless = st.checkbox("Run headless (no browser window)", value=True)
debug = st.checkbox("Debug mode (extra logs)", value=False)

if st.button("🚀 Scrape Reviews"):
    if not product_name.strip():
        st.warning("Please enter a product name.")
    else:
        with st.spinner("Scraping reviews — this may take a minute..."):
            scraper = None
            df = None
            try:
                scraper = ScrapeReviews(
                    product_name=product_name.strip(),
                    no_of_products=int(no_of_products),
                    headless=headless,
                    debug=debug,
                )
                df = scraper.get_review_data()
            except Exception as e:
                st.error(f"Scraping error: {e}")
                if debug:
                    st.text(traceback.format_exc())
                df = None
            finally:
                try:
                    if scraper is not None and hasattr(scraper, "close"):
                        scraper.close()
                except Exception:
                    if debug:
                        st.text("Error while closing scraper:")
                        st.text(traceback.format_exc())

            if df is None or (hasattr(df, "empty") and df.empty):
                st.error("No reviews found. Try a different query or set headless=False for debugging.")
            else:
                st.success(f"Scraped {len(df)} reviews.")
                st.dataframe(df)

                # Save to MongoDB
                try:
                    mongoio = MongoIO()
                    mongoio.store_reviews(product_name.strip(), df)
                    st.info("Saved reviews to MongoDB.")
                    st.session_state["data"] = True
                    st.session_state[SESSION_PRODUCT_KEY] = product_name.strip()
                except Exception as e:
                    st.error(f"Failed to save to MongoDB: {e}")
                    if debug:
                        st.text(traceback.format_exc())
