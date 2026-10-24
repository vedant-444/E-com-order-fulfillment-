"""
Database Connection Manager
Provides unified connection handling for SQLite, DuckDB, or PostgreSQL
"""

import sqlite3
import os
from pathlib import Path
from src.config import DB_PATH, WAREHOUSE_DATA_DIR

def get_db_connection():
    """Returns a SQLite connection with row factory enabled."""
    WAREHOUSE_DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def execute_script(script_text: str):
    """Executes a multi-statement SQL script."""
    conn = get_db_connection()
    try:
        conn.executescript(script_text)
        conn.commit()
    finally:
        conn.close()
