# src/scraper/scraper.py
import sys
import time
import random
from typing import List, Optional
from urllib.parse import urljoin

import pandas as pd
from bs4 import BeautifulSoup as bs
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

from src.exception import CustomException

class ScrapeReviews:
    def __init__(
        self,
        product_name: str,
        no_of_products: int = 1,
        headless: bool = True,
        debug: bool = False,
        wait_timeout: int = 12,
    ):
        try:
            self.product_name = product_name
            self.no_of_products = int(no_of_products)
            self.debug = debug
            self.wait_timeout = wait_timeout

            options = Options()
            if headless:
                options.add_argument("--headless=new")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--log-level=3")
            options.add_argument(
                "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
            )

            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            self.wait = WebDriverWait(self.driver, self.wait_timeout)

            if self.debug:
                print(f"[DEBUG] WebDriver started (headless={headless})")

        except Exception as e:
            try:
                if hasattr(self, "driver") and self.driver:
                    self.driver.quit()
            except Exception:
                pass
            raise CustomException(e, sys)

    def _random_sleep(self, a: float = 0.8, b: float = 1.8):
        time.sleep(random.uniform(a, b))

    def scrape_product_urls(self) -> List[str]:
        try:
            query = self.product_name.strip().replace(" ", "-")
            url = f"https://www.myntra.com/{query}"
            if self.debug:
                print("[DEBUG] Searching:", url)

            try:
                self.driver.get(url)
            except WebDriverException as e:
                if self.debug:
                    print("[ERROR] Failed to load search page:", e)
                raise

            self._random_sleep(1.0, 2.0)

            try:
                self.wait.until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li.product-base a[href], ul.results-base li a[href]"))
                )
            except TimeoutException:
                if self.debug:
                    print("[WARN] product list did not appear quickly; continuing with current page source")

            soup = bs(self.driver.page_source, "html.parser")
            anchors = soup.select("li.product-base a[href], ul.results-base li a[href], a[href^='/p/'], a[href*='/product/']")
            product_links = []
            for a in anchors:
                href = a.get("href")
                if not href:
                    continue
                full_url = urljoin("https://www.myntra.com/", href)
                if "myntra.com" not in full_url:
                    if self.debug:
                        print("[DEBUG] skipping non-myntra url:", full_url)
                    continue
                if "/p/" in full_url or "/product/" in full_url or "/buy" in full_url:
                    product_links.append(full_url)

            seen = set()
            unique = []
            for link in product_links:
                if link not in seen:
                    seen.add(link)
                    unique.append(link)
                if len(unique) >= self.no_of_products:
                    break

            if self.debug:
                print(f"[DEBUG] Found {len(unique)} product URLs (requested {self.no_of_products})")

            return unique

        except Exception as e:
            raise CustomException(e, sys)

    def extract_reviews(self, product_url: str) -> Optional[str]:
        try:
            if self.debug:
                print("[DEBUG] Opening product page:", product_url)
            try:
                self.driver.get(product_url)
            except WebDriverException as e:
                if self.debug:
                    print("[ERROR] Failed to open product page:", e)
                raise

            self._random_sleep(1.0, 2.0)
            soup = bs(self.driver.page_source, "html.parser")

            review_anchor = (
                soup.select_one("a.detailed-reviews-allReviews")
                or soup.select_one("a[href*='reviews']")
                or soup.select_one("a.pdp-see-all-reviews")
                or soup.select_one("div.index-overallRating a")
            )

            if not review_anchor:
                if self.debug:
                    print("[DEBUG] No explicit review anchor found; will attempt parsing product page for review blocks")
                return product_url

            href = review_anchor.get("href")
            if not href:
                return product_url

            review_url = href if href.startswith("http") else urljoin("https://www.myntra.com/", href)
            if self.debug:
                print("[DEBUG] Found review/page URL:", review_url)
            return review_url

        except Exception as e:
            raise CustomException(e, sys)

    def scroll_to_load_reviews(self, pause_time: float = 1.0, max_scrolls: int = 30):
        try:
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            for _ in range(max_scrolls):
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(pause_time)
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
        except Exception:
            if self.debug:
                print("[DEBUG] scroll_to_load_reviews encountered an issue (ignored)")

    def extract_products(self, review_url: str) -> pd.DataFrame:
        try:
            if self.debug:
                print("[DEBUG] Extracting reviews from:", review_url)
            try:
                self.driver.get(review_url)
            except WebDriverException as e:
                if self.debug:
                    print("[ERROR] Failed to open review/product url:", e)
                raise

            self.scroll_to_load_reviews(pause_time=1.0, max_scrolls=25)
            page_html = bs(self.driver.page_source, "html.parser")

            review_blocks = page_html.select(
                "div.detailed-reviews-userReviewsContainer, div.user-review, li.user-review-item, div.index-reviewContainer, div.user-review-card, div.reviews"
            )

            if self.debug:
                print(f"[DEBUG] Found {len(review_blocks)} review blocks with selectors")

            reviews = []
            title_tag = page_html.find("title")
            product_title = title_tag.text.strip() if title_tag else "Unknown Product"

            for block in review_blocks:
                try:
                    rating_tag = block.select_one(".user-review-starRating, .rating, .index-starRating, span.rating, .star")
                    rating = rating_tag.get_text(strip=True) if rating_tag else None

                    comment_tag = block.select_one(".user-review-reviewTextWrapper, .review-text, p, .comments, .review")
                    comment = comment_tag.get_text(strip=True) if comment_tag else None

                    name_tag = block.select_one(".user-review-left span, .user-name, .reviewer, .name")
                    name = name_tag.get_text(strip=True) if name_tag else None

                    date_tag = block.select_one(".user-review-left span:nth-of-type(2), .review-date, .date")
                    date = date_tag.get_text(strip=True) if date_tag else None

                    price = None
                    price_tag = page_html.select_one(".pdp-price, .pdp-product-price, span.product-price, .price")
                    if price_tag:
                        price = price_tag.get_text(strip=True)

                    reviews.append(
                        {
                            "Product Name": product_title,
                            "Price": price,
                            "Date": date,
                            "Rating": rating,
                            "Name": name,
                            "Comment": comment,
                        }
                    )
                except Exception:
                    if self.debug:
                        print("[DEBUG] skipping a review block due to parsing error")
                    continue

            if not reviews:
                if self.debug:
                    print("[DEBUG] No reviews parsed from", review_url)
                return pd.DataFrame()

            df = pd.DataFrame(reviews, columns=["Product Name", "Price", "Date", "Rating", "Name", "Comment"])
            if self.debug:
                print(f"[DEBUG] Parsed {len(df)} reviews for {product_title}")
            return df

        except Exception as e:
            raise CustomException(e, sys)

    def get_review_data(self) -> pd.DataFrame:
        try:
            urls = self.scrape_product_urls()
            all_reviews: List[pd.DataFrame] = []

            for idx, url in enumerate(urls):
                if self.debug:
                    print(f"[DEBUG] Processing product {idx+1}/{len(urls)}: {url}")
                review_link = self.extract_reviews(url)
                if not review_link:
                    if self.debug:
                        print("[DEBUG] No review link for product:", url)
                    continue
                df = self.extract_products(review_link)
                if df is not None and not df.empty:
                    all_reviews.append(df)
                self._random_sleep(1.0, 2.0)

            if not all_reviews:
                if self.debug:
                    print("[DEBUG] No reviews collected at all")
                return pd.DataFrame()

            final_df = pd.concat(all_reviews, axis=0, ignore_index=True)
            if self.debug:
                print(f"[DEBUG] Total reviews collected: {len(final_df)}")
            return final_df

        except Exception as e:
            raise CustomException(e, sys)

    def close(self):
        try:
            if hasattr(self, "driver") and self.driver:
                try:
                    self.driver.quit()
                except Exception:
                    pass
                if self.debug:
                    print("[DEBUG] WebDriver closed")
        except Exception:
            pass
