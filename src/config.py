"""
OrderFlow360 Analytics Platform - Core Configuration
NIT Campus Hiring Assessment - Cloud Data Engineering
"""

import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
STAGING_DATA_DIR = DATA_DIR / "staging"
QUARANTINE_DATA_DIR = DATA_DIR / "quarantine"
WAREHOUSE_DATA_DIR = DATA_DIR / "warehouse"
REPORTS_DIR = BASE_DIR / "reports"
SQL_DIR = BASE_DIR / "sql"

# Source File Paths
SOURCE_CUSTOMER_MASTER = BASE_DIR / "customer_master_orders_v3.csv"
SOURCE_ORDER_TRANSACTIONS = BASE_DIR / "order_transactions_v3.csv"
SOURCE_ORDER_TRANSACTIONS_DIRTY = BASE_DIR / "order_transactions_dirty_v3.csv"
SOURCE_COURIER_SLA = BASE_DIR / "courier_sla_master_v3.csv"
SOURCE_DQ_ANSWER_KEY = BASE_DIR / "dq_answer_key_v3.csv"

# Database Configuration
DB_PATH = WAREHOUSE_DATA_DIR / "orderflow360_warehouse.db"

# Canonical Enums & Standardization Dictionaries
VALID_STATUSES = {"Delivered", "In-Transit", "Cancelled", "Returned"}

STATUS_NORMALIZATION_MAP = {
    "delivered": "Delivered",
    "delivered ": "Delivered",
    "in transit": "In-Transit",
    "in-transit": "In-Transit",
    "cancelled": "Cancelled",
    "canceled": "Cancelled",
    "returned": "Returned",
    "return": "Returned",
}

COURIER_CANONICAL_MAP = {
    "delhivery": "Delhivery",
    "blue dart": "Blue Dart",
    "bluedart": "Blue Dart",
    "dtdc": "DTDC",
    "ecom express": "Ecom Express",
    "ecom-express": "Ecom Express",
    "ecomexpress": "Ecom Express",
    "xpressbees": "XpressBees",
    "xpress bees": "XpressBees",
    "shadowfax": "Shadowfax",
    "india post": "India Post",
    "indiapost": "India Post",
    "speed post": "India Post",
    "ekart": "Ekart",
    "gati": "Gati",
}

CITY_ALIAS_MAP = {
    "bombay": "Mumbai",
    "bangalore": "Bengaluru",
    "calcutta": "Kolkata",
    "madras": "Chennai",
    "poona": "Pune",
    "new delhi": "Delhi",
}

SEGMENT_NORMALIZATION_MAP = {
    "corporate": "Corporate",
    "premium": "Premium",
    "regular": "Regular",
}
