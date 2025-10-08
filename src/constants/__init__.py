# src/constants/__init__.py

# Environment variable key for the MongoDB connection string
MONGO_DB_URL_KEY: str = "MONGO_DB_URL"

# Default database name if not set in environment
MONGO_DATABASE_NAME: str = "myntra-reviews"

# Session key used in Streamlit session_state to store selected product
SESSION_PRODUCT_KEY: str = "product_name"
