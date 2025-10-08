# src/data_report/generate_data_report.py
import io
import math
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import matplotlib.pyplot as plt

from typing import Optional, List, Dict
from collections import Counter

# optional imports (graceful fallback)
try:
    from wordcloud import WordCloud
    HAS_WORDCLOUD = True
except Exception:
    HAS_WORDCLOUD = False

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    VADER = SentimentIntensityAnalyzer()
    HAS_VADER = True
except Exception:
    HAS_VADER = False

try:
    from textblob import TextBlob
    HAS_TEXTBLOB = True
except Exception:
    HAS_TEXTBLOB = False

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    HAS_SKLEARN = True
except Exception:
    HAS_SKLEARN = False

# helper functions
def _to_numeric_price(s: Optional[str]) -> Optional[float]:
    if s is None:
        return None
    s = str(s)
    # remove non-digit/decimal chars
    s = "".join(ch for ch in s if ch.isdigit() or ch == ".")
    if not s:
        return None
    try:
        return float(s)
    except Exception:
        return None

def _parse_date_try(date_str):
    if pd.isna(date_str):
        return None
    for fmt in ("%d %b %Y", "%d %B %Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return pd.to_datetime(date_str, format=fmt, errors="coerce")
        except Exception:
            continue
    # last resort
    try:
        return pd.to_datetime(date_str, errors="coerce")
    except Exception:
        return None

def _safe_mean(series):
    series = series.dropna()
    return series.mean() if not series.empty else None

def simple_sentiment(text: str) -> Dict[str, float]:
    """Return sentiment dict {'compound':..., 'polarity':...}. Uses VADER if available, else TextBlob polarity."""
    if not isinstance(text, str) or not text.strip():
        return {"compound": 0.0, "polarity": 0.0}
    if HAS_VADER:
        vs = VADER.polarity_scores(text)
        return {"compound": vs.get("compound", 0.0), "polarity": 0.0}
    if HAS_TEXTBLOB:
        try:
            tb = TextBlob(text)
            return {"compound": 0.0, "polarity": tb.sentiment.polarity}
        except Exception:
            return {"compound": 0.0, "polarity": 0.0}
    return {"compound": 0.0, "polarity": 0.0}

def get_top_keywords(corpus: List[str], top_n: int = 20) -> List[str]:
    """Return top_n keywords using TF-IDF when available, otherwise frequency."""
    corpus_clean = [c if isinstance(c, str) else "" for c in corpus]
    if HAS_SKLEARN:
        try:
            vectorizer = TfidfVectorizer(max_df=0.9, min_df=2, stop_words="english", ngram_range=(1,2), max_features=2000)
            X = vectorizer.fit_transform(corpus_clean)
            sums = np.asarray(X.sum(axis=0)).ravel()
            terms = vectorizer.get_feature_names_out()
            top_idx = np.argsort(sums)[::-1][:top_n]
            return [terms[i] for i in top_idx]
        except Exception:
            pass
    # fallback frequency
    tokens = []
    for doc in corpus_clean:
        for tok in str(doc).lower().split():
            tok = tok.strip(".,!?:;\"'()[]{}")
            if len(tok) > 2:
                tokens.append(tok)
    common = Counter(tokens).most_common(top_n)
    return [t for t, _ in common]

# Main dashboard class
class DashboardGenerator:
    def __init__(self, data: pd.DataFrame):
        # copy + normalize expected columns
        self.data = data.copy()
        # unify common column names (lowercase keys)
        cols = {c.lower(): c for c in self.data.columns}
        # keep canonical names internally
        if "rating" in cols:
            self.data["Rating"] = pd.to_numeric(self.data[cols["rating"]], errors="coerce")
        if "price" in cols:
            # convert price to numeric safe
            self.data["Price"] = self.data[cols["price"]].apply(_to_numeric_price)
        if "product name" in cols:
            self.data["Product Name"] = self.data[cols["product name"]]
        if "comment" in cols:
            self.data["Comment"] = self.data[cols["comment"]].astype(str)
        if "name" in cols:
            self.data["Name"] = self.data[cols["name"]]
        if "date" in cols:
            self.data["Date"] = pd.to_datetime(self.data[cols["date"]], errors="coerce")

        # Derived columns
        if "Comment" in self.data.columns:
            self.data["Review Length"] = self.data["Comment"].fillna("").str.len()
        if "Date" in self.data.columns:
            # ensure Date is datetime if possible
            try:
                self.data["Date"] = pd.to_datetime(self.data["Date"], errors="coerce")
            except Exception:
                pass

        # sentiment column (lazy compute)
        self._sentiment_computed = False

    def compute_sentiment(self):
        if self._sentiment_computed:
            return
        if "Comment" not in self.data.columns:
            self.data["sent_compound"] = 0.0
            self.data["sent_polarity"] = 0.0
            self._sentiment_computed = True
            return
        compounds, pols = [], []
        for txt in self.data["Comment"].fillna("").astype(str).tolist():
            s = simple_sentiment(txt)
            compounds.append(s.get("compound", 0.0))
            pols.append(s.get("polarity", 0.0))
        self.data["sent_compound"] = compounds
        self.data["sent_polarity"] = pols
        self._sentiment_computed = True

    # Display functions
    def display_header(self):
        st.title("📊 Reviews Dashboard")
        st.write(f"Total reviews: **{len(self.data)}**")
        if "Product Name" in self.data.columns:
            st.write("Products in dataset:", ", ".join(self.data["Product Name"].unique()[:10]))

    def display_rating_breakdown(self):
        st.subheader("⭐ Rating breakdown")
        if "Rating" not in self.data.columns or self.data["Rating"].dropna().empty:
            st.info("No numeric rating data available.")
            return
        df = self.data.dropna(subset=["Rating"])
        counts = df["Rating"].round(0).value_counts().sort_index()
        fig = px.bar(x=counts.index.astype(str), y=counts.values, labels={"x":"Stars", "y":"Count"}, title="Star rating counts")
        st.plotly_chart(fig, use_container_width=True)

        st.markdown(f"**Average rating:** {df['Rating'].mean():.2f} (n={len(df)})")
        st.markdown(f"**Median rating:** {df['Rating'].median():.2f}")

    def display_rating_over_time(self):
        st.subheader("🕒 Rating over time")
        if "Date" not in self.data.columns or self.data["Date"].isnull().all():
            st.info("No date information available.")
            return
        tmp = self.data.dropna(subset=["Date", "Rating"]).copy()
        if tmp.empty:
            st.info("No data with both date and rating.")
            return
        tmp["Month"] = tmp["Date"].dt.to_period("M").dt.to_timestamp()
        agg = tmp.groupby("Month", as_index=False)["Rating"].mean()
        fig = px.line(agg, x="Month", y="Rating", title="Average rating by month")
        st.plotly_chart(fig, use_container_width=True)

    def display_price_vs_rating(self):
        st.subheader("💰 Price vs Rating")
        if "Price" not in self.data.columns or self.data["Price"].dropna().empty:
            st.info("No price data available.")
            return
        tmp = self.data.dropna(subset=["Price", "Rating"])
        if tmp.empty:
            st.info("No data with both price and rating.")
            return
        # create bins for price (log-scale if needed)
        tmp["price_bin"] = pd.qcut(tmp["Price"], q=min(6, max(2, tmp["Price"].nunique())), duplicates="drop")
        agg = tmp.groupby("price_bin", as_index=False)["Rating"].mean().sort_values(by="Rating", ascending=False)
        fig = px.bar(agg, x="price_bin", y="Rating", title="Average rating by price bin")
        st.plotly_chart(fig, use_container_width=True)

        # scatter
        fig2 = px.scatter(tmp.sample(min(len(tmp), 1000)), x="Price", y="Rating", trendline="ols", title="Rating vs Price (sampled)")
        st.plotly_chart(fig2, use_container_width=True)

    def display_review_length(self):
        st.subheader("✍️ Review length distribution")
        if "Review Length" not in self.data.columns:
            st.info("No comments to compute lengths.")
            return
        fig = px.histogram(self.data, x="Review Length", nbins=40, title="Review length (characters)")
        st.plotly_chart(fig, use_container_width=True)

    def display_top_reviewers(self, top_n: int = 10):
        st.subheader("👤 Top reviewers")
        if "Name" not in self.data.columns:
            st.info("Reviewer names not available.")
            return
        top = self.data["Name"].fillna("Unknown").value_counts().head(top_n)
        st.table(top.reset_index().rename(columns={"index":"Reviewer", "Name":"Reviews"}))

    def display_top_keywords(self, top_n: int = 20):
        st.subheader("🔎 Top keywords in reviews")
        if "Comment" not in self.data.columns or self.data["Comment"].dropna().empty:
            st.info("No reviews available for keyword extraction.")
            return
        keywords = get_top_keywords(self.data["Comment"].fillna("").tolist(), top_n=top_n)
        st.write(", ".join(keywords))

    def display_wordcloud(self, width: int = 800, height: int = 400):
        st.subheader("☁️ Word Cloud (from reviews)")
        if not HAS_WORDCLOUD:
            st.info("Install `wordcloud` to view this visualization (pip install wordcloud).")
            return
        text = " ".join(self.data["Comment"].dropna().astype(str).tolist())
        if not text.strip():
            st.info("No textual content for word cloud.")
            return
        wc = WordCloud(width=width, height=height, background_color="white", stopwords=set()).generate(text)
        fig, ax = plt.subplots(figsize=(width/100, height/100))
        ax.imshow(wc, interpolation="bilinear")
        ax.axis("off")
        st.pyplot(fig)

    def display_sentiment_summary(self):
        st.subheader("🙂 Sentiment summary")
        # compute sentiment lazily
        self.compute_sentiment()
        if "sent_compound" not in self.data.columns and "sent_polarity" not in self.data.columns:
            st.info("No sentiment metrics available.")
            return
        # prefer VADER compound if present
        if "sent_compound" in self.data.columns:
            ser = self.data["sent_compound"].dropna()
            st.markdown(f"**Mean VADER compound:** {ser.mean():.3f}")
            fig = px.histogram(ser, nbins=30, title="VADER compound distribution")
            st.plotly_chart(fig, use_container_width=True)
        elif "sent_polarity" in self.data.columns:
            ser = self.data["sent_polarity"].dropna()
            st.markdown(f"**Mean polarity:** {ser.mean():.3f}")
            fig = px.histogram(ser, nbins=30, title="TextBlob polarity distribution")
            st.plotly_chart(fig, use_container_width=True)

    def display_top_positive_negative_reviews(self, top_n: int = 5):
        st.subheader("🔝 Top positive and negative reviews")
        # ensure sentiment
        self.compute_sentiment()
        df = self.data.copy()
        if "sent_compound" in df.columns and not df["sent_compound"].isnull().all():
            s_col = "sent_compound"
        elif "Rating" in df.columns and not df["Rating"].isnull().all():
            # fallback to Rating
            df["rating_rank"] = df["Rating"].fillna(0)
            s_col = "rating_rank"
        else:
            st.info("No sentiment or rating info to rank reviews.")
            return

        pos = df.sort_values(by=s_col, ascending=False).head(top_n)
        neg = df.sort_values(by=s_col, ascending=True).head(top_n)

        st.markdown("**Top positive reviews**")
        for _, r in pos.iterrows():
            st.info(f"⭐ {r.get('Rating','')} — {r.get('Comment','')[:400]}")
        st.markdown("**Top negative reviews**")
        for _, r in neg.iterrows():
            st.error(f"💬 {r.get('Rating','')} — {r.get('Comment','')[:400]}")

    def display_rating_heatmap(self):
        st.subheader("🔢 Rating heatmap (product×rating) — if multiple products")
        if "Product Name" not in self.data.columns or "Rating" not in self.data.columns:
            st.info("Need both Product Name and Rating columns.")
            return
        pivot = (self.data
                 .dropna(subset=["Product Name", "Rating"])
                 .assign(RatingRound=lambda d: d["Rating"].round(0))
                 .groupby(["Product Name", "RatingRound"]).size().unstack(fill_value=0))
        if pivot.empty:
            st.info("No data for heatmap.")
            return
        fig = px.imshow(pivot, labels=dict(x="Rating", y="Product", color="Count"), title="Counts by product and rounded rating")
        st.plotly_chart(fig, use_container_width=True)

    # top-level runner to place everything in order
    def run_all(self, show_wordcloud: bool = True, top_n_keywords: int = 20, top_reviewers_n: int = 10):
        self.display_header()
        self.display_rating_breakdown()
        self.display_rating_over_time()
        self.display_rating_heatmap()
        self.display_price_vs_rating()
        self.display_review_length()
        self.display_top_reviewers(top_reviewers_n)
        self.display_top_keywords(top_n_keywords)
        if show_wordcloud:
            self.display_wordcloud()
        self.display_sentiment_summary()
        self.display_top_positive_negative_reviews(top_n=5)
