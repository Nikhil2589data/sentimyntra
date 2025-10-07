# src/data_report/generate_data_report.py
import streamlit as st
import pandas as pd
import plotly.express as px

class DashboardGenerator:
    def __init__(self, data: pd.DataFrame):
        self.data = data.copy()
        # Normalize numeric columns
        if "Rating" in self.data.columns:
            self.data["Rating"] = pd.to_numeric(self.data["Rating"], errors="coerce")
        if "Price" in self.data.columns:
            self.data["Price"] = (
                self.data["Price"].astype(str)
                .str.replace("₹", "", regex=False)
                .str.replace(",", "", regex=False)
            )
            self.data["Price"] = pd.to_numeric(self.data["Price"], errors="coerce")

    def display_general_info(self):
        st.header("📊 General Information")

        # Ratings distribution
        if "Rating" in self.data.columns and not self.data["Rating"].isnull().all():
            st.subheader("⭐ Ratings Distribution")
            fig = px.histogram(self.data, x="Rating", nbins=10, title="Rating distribution")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No numeric Rating data available for distribution.")

        # Average rating per product
        st.subheader("🌟 Average Rating per Product")
        if "Product Name" in self.data.columns and "Rating" in self.data.columns:
            avg_rating = self.data.groupby("Product Name", as_index=False)["Rating"].mean().dropna()
            if not avg_rating.empty:
                fig = px.bar(avg_rating, x="Product Name", y="Rating",
                             title="Average rating by product", color="Product Name")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.write("No rating data to plot.")
        else:
            st.write("Product Name or Rating column missing.")

        # Average price per product (if Price exists)
        if "Price" in self.data.columns and not self.data["Price"].isnull().all():
            st.subheader("💰 Average Price per Product")
            avg_price = self.data.groupby("Product Name", as_index=False)["Price"].mean().dropna()
            if not avg_price.empty:
                fig = px.bar(avg_price, x="Product Name", y="Price",
                             title="Average price by product", color="Product Name")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.write("No price data to plot.")

    def display_product_sections(self):
        st.header("🧾 Product-level Insights")
        if "Product Name" not in self.data.columns:
            st.write("No Product Name column found.")
            return

        for product in self.data["Product Name"].unique():
            st.subheader(f"📦 {product}")
            subset = self.data[self.data["Product Name"] == product]

            # Average rating
            if "Rating" in subset.columns and not subset["Rating"].isnull().all():
                st.markdown(f"**Average Rating:** {subset['Rating'].mean():.2f}")
            else:
                st.markdown("**Average Rating:** N/A")

            # Top positive reviews
            st.markdown("**Top positive reviews**")
            if "Rating" in subset.columns:
                positives = subset[subset["Rating"] >= 4.5].head(5)
            else:
                positives = pd.DataFrame()
            if not positives.empty:
                for _, r in positives.iterrows():
                    st.info(f"⭐ {r.get('Rating', '')} — {r.get('Comment', '')}")
            else:
                st.write("_No strong positive reviews found._")

            # Top negative reviews
            st.markdown("**Top negative reviews**")
            if "Rating" in subset.columns:
                negatives = subset[subset["Rating"] <= 2].head(5)
            else:
                negatives = pd.DataFrame()
            if not negatives.empty:
                for _, r in negatives.iterrows():
                    st.error(f"💬 {r.get('Rating', '')} — {r.get('Comment', '')}")
            else:
                st.write("_No strong negative reviews found._")

            st.markdown("---")
