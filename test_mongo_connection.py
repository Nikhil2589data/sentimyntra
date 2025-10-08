from dotenv import load_dotenv
import os
from pymongo import MongoClient

load_dotenv()
uri = os.getenv("MONGO_DB_URL")
print("uri ok?", bool(uri))

if uri:
    try:
        client = MongoClient(
            uri,
            serverSelectionTimeoutMS=15000,  # wait up to 15s
            retryWrites=True,
            tls=True
        )
        print("✅ Connection successful! Available databases:")
        print(client.list_database_names())
    except Exception as e:
        print("❌ Mongo error:", type(e).__name__, str(e))
else:
    print("❌ No MONGO_DB_URL found in .env file")
