# src/cloud_io/__init__.py
import os
from typing import Optional, List, Dict, Any
import sys

import pandas as pd
from pymongo import MongoClient, errors
from dotenv import load_dotenv

from src.constants import MONGO_DATABASE_NAME
from src.exception import CustomException

load_dotenv()


def _normalize_collection_name(name: str) -> str:
    """Make a safe collection name from product name."""
    return name.strip().replace(" ", "_").lower()


class MongoIO:
    """
    Simple MongoDB helper using pymongo.

    Exposes:
      - store_reviews(product_name, reviews: pd.DataFrame)
      - get_reviews(product_name) -> pd.DataFrame
      - list_collections() -> List[str]
      - drop_collection(product_name) -> None (careful)
    """

    def __init__(self, uri: Optional[str] = None, database_name: Optional[str] = None):
        try:
            self.uri = uri or os.getenv("MONGO_DB_URL")
            if not self.uri:
                raise Exception("MONGO_DB_URL not set in environment (.env)")

            self.database_name = database_name or os.getenv("MONGO_DATABASE_NAME") or MONGO_DATABASE_NAME
            # Create client with reasonable timeouts
            self.client = MongoClient(self.uri, serverSelectionTimeoutMS=10000, connectTimeoutMS=10000)
            # quick server selection to validate connection (will raise if cannot connect)
            self.client.server_info()
            self.db = self.client[self.database_name]
        except Exception as e:
            # Wrap with CustomException so rest of app has consistent error handling
            raise CustomException(e, sys)

    def store_reviews(self, product_name: str, reviews: pd.DataFrame) -> int:
        """
        Insert reviews dataframe into a collection named after the product.
        Returns number of documents inserted.
        """
        try:
            if reviews is None or reviews.empty:
                return 0

            collection_name = _normalize_collection_name(product_name)
            records = reviews.to_dict(orient="records")
            if not records:
                return 0

            result = self.db[collection_name].insert_many(records)
            inserted = len(result.inserted_ids)
            print(f"[MongoIO] Inserted {inserted} documents into '{collection_name}'")
            return inserted
        except Exception as e:
            raise CustomException(e, sys)

    def get_reviews(self, product_name: str) -> pd.DataFrame:
        """
        Fetch all reviews for the given product as a pandas DataFrame.
        Returns empty DataFrame if none found.
        """
        try:
            collection_name = _normalize_collection_name(product_name)
            cursor = self.db[collection_name].find({}, {"_id": 0})
            data = list(cursor)
            if not data:
                return pd.DataFrame()
            return pd.DataFrame(data)
        except Exception as e:
            raise CustomException(e, sys)

    def list_collections(self) -> List[str]:
        """Return list of collection names in the configured database."""
        try:
            return self.db.list_collection_names()
        except Exception as e:
            raise CustomException(e, sys)

    def drop_collection(self, product_name: str) -> bool:
        """
        Danger: Drop the collection for the product.
        Returns True if dropped.
        """
        try:
            collection_name = _normalize_collection_name(product_name)
            self.db.drop_collection(collection_name)
            return True
        except Exception as e:
            raise CustomException(e, sys)
