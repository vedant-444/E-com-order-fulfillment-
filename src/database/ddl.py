"""
Database DDL Execution Module
Initializes Staging, Star Schema, and Audit tables
"""

from src.config import SQL_DIR
from src.database.connection import execute_script

def init_database():
    """Reads and executes all DDL scripts in sequence."""
    ddl_scripts = [
        SQL_DIR / "ddl" / "01_create_staging_tables.sql",
        SQL_DIR / "ddl" / "02_create_star_schema.sql",
        SQL_DIR / "ddl" / "03_create_audit_tables.sql",
    ]
    
    for script_path in ddl_scripts:
        if script_path.exists():
            with open(script_path, "r", encoding="utf-8") as f:
                script_sql = f.read()
                execute_script(script_sql)
            print(f"[DDL] Successfully applied: {script_path.name}")
        else:
            print(f"[DDL] Script not found: {script_path}")

if __name__ == "__main__":
    init_database()
