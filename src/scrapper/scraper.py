# src/scrapper/scraper.py
import os
import sys
import time
import random
from typing import List, Optional

import pandas as pd
from bs4 import BeautifulSoup as bs
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException, TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

from src.exception import CustomException


class ScrapeReviews:
    def __init__(
        self,
        product_name: str,
        no_of_products: int,
        headless: bool = True,
        debug: bool = False,
        wait_timeout: int = 12,
        max_scrolls: int = 20,
    ):
        """
        Robust scraper initialization.

        :param product_name: search term on Myntra
        :param no_of_products: how many product pages to scrape (not number of reviews)
        :param headless: run Chrome headless or visible (use False while debugging)
        :param debug: print debug logs to console
        :param wait_timeout: selenium explicit wait timeout (seconds)
        :param max_scrolls: scroll attempts for lazy-load pages
        """
        try:
            self.product_name = product_name
            self.no_of_products = int(no_of_products)
            self.debug = debug
            self.wait_timeout = wait_timeout
            self.max_scrolls = max_scrolls

            options = Options()
            if headless:
                # modern headless flag; fallback handled by browser
                try:
                    options.add_argument("--headless=new")
                except Exception:
                    options.add_argument("--headless")
                options.add_argument("--disable-gpu")
            # common safe flags
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--log-level=3")
            options.add_argument(
                "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
            )

            # try to detect chrome binary if required (optional)
            possible_binaries = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            ]
            for p in possible_binaries:
                if os.path.exists(p):
                    options.binary_location = p
                    break

            # create driver with webdriver-manager Service
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            self.wait = WebDriverWait(self.driver, self.wait_timeout)

            if self.debug:
                print("[DEBUG] WebDriver started (headless=%s)" % (headless,))

        except Exception as e:
            raise CustomException(e, sys)

    def _sleep(self, a: float = 0.8, b: float = 1.6):
        time.sleep(random.uniform(a, b))

    def _scroll_down(self, pause: float = 1.0, max_scrolls: Optional[int] = None):
        max_scrolls = max_scrolls or self.max_scrolls
        try:
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            for _ in range(max_scrolls):
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(pause)
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
        except Exception:
            # ignore scroll errors
            pass

    def scrape_product_urls(self) -> List[str]:
        """
        Collect product page URLs from Myntra search results using Selenium (handles JS).
        Returns up to self.no_of_products URLs.
        """
        try:
            q = self.product_name.strip().replace(" ", "-")
            search_url = f"https://www.myntra.com/{q}"
            if self.debug:
                print("[DEBUG] Searching:", search_url)

            # load page
            self.driver.get(search_url)
            # allow JS to fire
            time.sleep(2.5)
            # scroll a bit to trigger lazy loading
            self._scroll_down(pause=1.0, max_scrolls=3)

            # Try a set of selectors that commonly contain product items
            selectors = [
                "li.product-base a[href]",
                "ul.results-base li a[href]",
                "a.product-base",
                "a[href*='/p/']",
                "a[href*='/product/']",
            ]

            anchors = []
            for sel in selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, sel)
                    if elements:
                        if self.debug:
                            print(f"[DEBUG] selector '{sel}' returned {len(elements)} elements")
                        anchors = elements
                        break
                except Exception:
                    continue

            # fallback: find all anchors and filter heuristically
            if not anchors:
                anchors = self.driver.find_elements(By.CSS_SELECTOR, "a[href]")

            product_links = []
            for el in anchors:
                try:
                    href = el.get_attribute("href")
                    if not href:
                        continue
                    # heuristics - product pages usually contain '/p/', '/product', '/buy' or have myntra domain
                    if any(x in href for x in ["/p/", "/product", "/buy/", "/products/"]) or "myntra.com" in href:
                        # normalize to https if missing
                        if href.startswith("//"):
                            href = "https:" + href
                        product_links.append(href)
                except Exception:
                    continue
                if len(product_links) >= self.no_of_products:
                    break

            # dedupe preserving order
            seen = set()
            unique = []
            for u in product_links:
                if u not in seen:
                    seen.add(u)
                    unique.append(u)
            if self.debug:
                print(f"[DEBUG] Found {len(unique)} product URLs")
                for i, u in enumerate(unique[:10]):
                    if self.debug:
                        print(f"  [{i}] {u}")

            return unique[: self.no_of_products]

        except Exception as e:
            raise CustomException(e, sys)

    def _try_click_review_anchor(self) -> bool:
        """
        Tries multiple strategies to click the 'all reviews' link on a product page.
        Returns True if a click/navigation occurred.
        """
        try_selectors = [
            ("css", "a.detailed-reviews-allReviews"),
            ("css", "a[href*='reviews']"),
            ("xpath", "//a[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'read all reviews')]"),
            ("xpath", "//a[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'all reviews')]"),
        ]
        for mode, sel in try_selectors:
            try:
                if mode == "css":
                    el = self.driver.find_element(By.CSS_SELECTOR, sel)
                else:
                    el = self.driver.find_element(By.XPATH, sel)
                if el:
                    try:
                        el.click()
                    except Exception:
                        # try JS click as fallback
                        self.driver.execute_script("arguments[0].click();", el)
                    self._sleep(1.0, 1.6)
                    if self.debug:
                        print(f"[DEBUG] Clicked reviews anchor with selector: {sel}")
                    return True
            except Exception:
                continue
        return False

    def extract_reviews(self, product_url: str) -> Optional[str]:
        """
        Given a product page URL, try to find the review page/link.
        Returns a full URL to the review page (or product_url if reviews are on same page),
        or None if not found.
        """
        try:
            if self.debug:
                print("[DEBUG] Opening product page:", product_url)
            self.driver.get(product_url)
            time.sleep(2.0)
            # attempt to click 'all reviews' if present
            clicked = self._try_click_review_anchor()
            # after clicking or not, scroll to load content
            self._scroll_down(pause=1.0, max_scrolls=5)
            # try to get current URL — if clicking navigated to a reviews page it may change
            current = self.driver.current_url
            # determine if current page has review blocks
            soup = bs(self.driver.page_source, "html.parser")
            # checks for review blocks
            if soup.select("div.user-review, li.user-review-item, div.detailed-reviews-userReviewsContainer, .ratings"):
                if self.debug:
                    print("[DEBUG] Reviews found on page (product or review page)")
                return current
            # if click navigated to an anchor (href), return that
            if clicked:
                return current
            # try to find anchor href via BS as fallback
            anchor = soup.select_one("a.detailed-reviews-allReviews, a[href*='reviews']")
            if anchor:
                href = anchor.get("href")
                if href and not href.startswith("http"):
                    href = "https://www.myntra.com" + href
                return href
            # no reviews link found
            if self.debug:
                print("[DEBUG] No review link/blocks found for this product")
            return None
        except Exception as e:
            raise CustomException(e, sys)

    def extract_products(self, review_page_url: str) -> pd.DataFrame:
        """
        Given a URL that contains reviews (either product page or dedicated review page),
        parse review blocks and return a DataFrame.
        """
        try:
            if self.debug:
                print("[DEBUG] Opening review/page URL:", review_page_url)
            self.driver.get(review_page_url)
            # scroll to load lazy reviews
            self._scroll_down(pause=1.0, max_scrolls=self.max_scrolls)
            time.sleep(1.0)

            soup = bs(self.driver.page_source, "html.parser")

            # selectors for review containers (multiple tries)
            review_selectors = [
                "div.detailed-reviews-userReviewsContainer",
                "li.user-review-item",
                "div.user-review",
                "div.review",
                ".ratingReviews"
            ]
            blocks = []
            for sel in review_selectors:
                found = soup.select(sel)
                if found:
                    blocks = found
                    if self.debug:
                        print(f"[DEBUG] Found {len(found)} review blocks with selector: {sel}")
                    break

            # if still none, return empty df
            if not blocks:
                if self.debug:
                    print("[DEBUG] No review blocks found on page")
                return pd.DataFrame()

            # product meta
            title_tag = soup.find("title")
            product_title = title_tag.text.strip() if title_tag else "Unknown Product"

            reviews = []
            for b in blocks:
                try:
                    # rating
                    rating_el = b.select_one(".user-review-starRating, .rating, .star-rating, .index-starRating")
                    rating = rating_el.get_text(strip=True) if rating_el else None
                    # comment
                    comment_el = b.select_one(".user-review-reviewTextWrapper, .review-text, p, .comment")
                    comment = comment_el.get_text(strip=True) if comment_el else None
                    # name
                    name_el = b.select_one(".user-review-left span, .user-name, .reviewer, .author")
                    name = name_el.get_text(strip=True) if name_el else None
                    # date
                    date_el = b.select_one(".user-review-left span:nth-of-type(2), .review-date, .date")
                    date = date_el.get_text(strip=True) if date_el else None

                    if not comment and not rating:
                        continue

                    reviews.append(
                        {
                            "Product Name": product_title,
                            "Over_All_Rating": None,
                            "Price": None,
                            "Date": date,
                            "Rating": rating,
                            "Name": name,
                            "Comment": comment,
                        }
                    )
                except Exception:
                    continue

            df = pd.DataFrame(reviews, columns=["Product Name", "Over_All_Rating", "Price", "Date", "Rating", "Name", "Comment"])
            if self.debug:
                print(f"[DEBUG] Parsed {len(df)} reviews for {product_title}")
            return df

        except Exception as e:
            raise CustomException(e, sys)

    def get_review_data(self) -> pd.DataFrame:
        """
        Main method: orchestrates getting product urls, then extracting reviews.
        """
        try:
            product_urls = self.scrape_product_urls()
            if not product_urls:
                if self.debug:
                    print("[DEBUG] No product URLs found")
                return pd.DataFrame()

            collected = []
            for idx, purl in enumerate(product_urls):
                try:
                    if self.debug:
                        print(f"[DEBUG] Processing product {idx + 1}/{len(product_urls)}: {purl}")
                    review_page = self.extract_reviews(purl)
                    if review_page:
                        df = self.extract_products(review_page)
                        if df is not None and not df.empty:
                            collected.append(df)
                    else:
                        if self.debug:
                            print("[DEBUG] No reviews link/page for this product")
                    # small pause between product fetches
                    self._sleep(1.5, 2.5)
                except Exception:
                    # continue with next product on individual failure
                    continue

            if not collected:
                if self.debug:
                    print("[DEBUG] No reviews collected at all")
                return pd.DataFrame()

            result = pd.concat(collected, ignore_index=True)
            if self.debug:
                print(f"[DEBUG] Total reviews collected: {len(result)}")
            return result

        except Exception as e:
            raise CustomException(e, sys)
        finally:
            # keep driver alive for caller's close() if they want; but attempt safe quit if unexpected
            try:
                if hasattr(self, "driver") and self.driver:
                    # do not always quit here to allow caller to call close()
                    pass
            except Exception:
                pass

    def close(self):
        """Close the browser cleanly."""
        try:
            if hasattr(self, "driver") and self.driver:
                self.driver.quit()
                if self.debug:
                    print("[DEBUG] WebDriver closed")
        except Exception:
            pass
