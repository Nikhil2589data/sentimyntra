# src/utils/__init__.py
from functools import lru_cache
from typing import List
import sys

from src.cloud_io import MongoIO
from src.exception import CustomException

@lru_cache(maxsize=1)
def fetch_product_names_from_cloud(title_case: bool = True, exclude_system: bool = True) -> List[str]:
    try:
        mongo = MongoIO()
        collection_names = mongo.list_collections(exclude_system=exclude_system)
        cleaned = []
        for name in collection_names:
            s = name.replace("_", " ").strip()
            s = s.title() if title_case else s
            cleaned.append(s)
        return sorted(cleaned)
    except Exception as e:
        raise CustomException(e, sys)
