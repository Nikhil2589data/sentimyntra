# test_store.py
from dotenv import load_dotenv
import os
import pandas as pd
from src.cloud_io import MongoIO

load_dotenv()
mongo = MongoIO()
print("Collections before:", mongo.list_collections())

# small sample dataframe
df = pd.DataFrame([{
    "Product Name": "test-product",
    "Over_All_Rating": 4.5,
    "Price": "₹499",
    "Date": "2025-10-06",
    "Rating": 5,
    "Name": "Unit Tester",
    "Comment": "Test comment"
}])

inserted = mongo.store_reviews("test-product", df)
print("Inserted:", inserted)

fetched = mongo.get_reviews("test-product")
print("Fetched rows:", len(fetched))
print(fetched.head())

# cleanup if you want
# mongo.drop_collection("test-product")
