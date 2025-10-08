# src/cloud_io/__init__.py
import os
import sys
from typing import Optional, List
import pandas as pd
from pymongo import MongoClient
from dotenv import load_dotenv

from src.constants import MONGO_DB_URL_KEY, MONGO_DATABASE_NAME
from src.exception import CustomException

load_dotenv()

def _normalize_collection_name(name: str) -> str:
    return name.strip().replace(" ", "_").lower()

class MongoIO:
    def __init__(self, uri: Optional[str] = None, database_name: Optional[str] = None):
        try:
            self.uri = uri or os.getenv(MONGO_DB_URL_KEY)
            if not self.uri:
                raise Exception(f"{MONGO_DB_URL_KEY} not set in environment (.env)")

            self.database_name = database_name or os.getenv("MONGO_DATABASE_NAME") or MONGO_DATABASE_NAME

            client_kwargs = dict(serverSelectionTimeoutMS=10000, connectTimeoutMS=10000)
            if self.uri.startswith("mongodb+srv://"):
                client_kwargs["tls"] = True

            self.client = MongoClient(self.uri, **client_kwargs)
            self.client.server_info()
            self.db = self.client[self.database_name]
        except Exception as e:
            raise CustomException(e, sys)

    def store_reviews(self, product_name: str, reviews: pd.DataFrame) -> int:
        try:
            if reviews is None:
                return 0
            if hasattr(reviews, "empty") and reviews.empty:
                return 0

            collection_name = _normalize_collection_name(product_name)
            if isinstance(reviews, pd.DataFrame):
                records = reviews.to_dict(orient="records")
            else:
                records = list(reviews) if isinstance(reviews, (list, tuple)) else []

            if not records:
                return 0

            result = self.db[collection_name].insert_many(records)
            inserted = len(result.inserted_ids)
            print(f"[MongoIO] Inserted {inserted} documents into '{collection_name}'")
            return inserted
        except Exception as e:
            raise CustomException(e, sys)

    def get_reviews(self, product_name: str) -> pd.DataFrame:
        try:
            collection_name = _normalize_collection_name(product_name)
            cursor = self.db[collection_name].find({}, {"_id": 0})
            data = list(cursor)
            if not data:
                return pd.DataFrame()
            return pd.DataFrame(data)
        except Exception as e:
            raise CustomException(e, sys)

    def list_collections(self, exclude_system: bool = True) -> List[str]:
        try:
            names = self.db.list_collection_names()
            if exclude_system:
                names = [n for n in names if not n.startswith("system.")]
            return names
        except Exception as e:
            raise CustomException(e, sys)

    def drop_collection(self, product_name: str) -> bool:
        try:
            collection_name = _normalize_collection_name(product_name)
            if collection_name not in self.db.list_collection_names():
                return False
            self.db.drop_collection(collection_name)
            return True
        except Exception as e:
            raise CustomException(e, sys)
