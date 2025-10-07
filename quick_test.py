from src.scrapper.scraper import ScrapeReviews

# Create a scraper object
scraper = ScrapeReviews("tshirt", 2, headless=False, debug=True)

# Start scraping
df = scraper.get_review_data()

# Display some results
print(df.head())
print("Total:", len(df))

# Close browser safely
scraper.close()
