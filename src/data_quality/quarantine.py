"""
Quarantine and Audit Log Handler
Stores quarantined rejected records and writes audit logs to database and files
"""

import csv
import json
from datetime import datetime
from src.config import QUARANTINE_DATA_DIR
from src.database.connection import get_db_connection

class QuarantineManager:
    def __init__(self):
        QUARANTINE_DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.rejected_records = []
        self.audit_entries = []

    def log_issue(self, file_name: str, record_key: str, rule_name: str, 
                  severity: str, action_taken: str, error_message: str, raw_payload: dict):
        """Records an audit issue."""
        entry = {
            "file_name": file_name,
            "record_key": str(record_key or "N/A"),
            "rule_name": rule_name,
            "severity": severity,
            "action_taken": action_taken,
            "error_message": error_message,
            "raw_payload": json.dumps(raw_payload) if isinstance(raw_payload, dict) else str(raw_payload),
            "log_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.audit_entries.append(entry)
        
        if severity in {"REJECT", "QUARANTINE"}:
            payload_copy = dict(raw_payload) if isinstance(raw_payload, dict) else {"raw": str(raw_payload)}
            payload_copy["_REJECTION_RULE"] = rule_name
            payload_copy["_REJECTION_REASON"] = error_message
            self.rejected_records.append(payload_copy)

    def persist(self):
        """Writes audit logs to SQLite DQ_AUDIT_LOG and exports quarantine CSV."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        insert_sql = """
        INSERT INTO DQ_AUDIT_LOG (
            FILE_NAME, RECORD_KEY, RULE_NAME, SEVERITY, ACTION_TAKEN, ERROR_MESSAGE, RAW_PAYLOAD, LOG_TIMESTAMP
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        for e in self.audit_entries:
            cursor.execute(insert_sql, (
                e["file_name"],
                e["record_key"],
                e["rule_name"],
                e["severity"],
                e["action_taken"],
                e["error_message"],
                e["raw_payload"],
                e["log_timestamp"]
            ))
            
        conn.commit()
        conn.close()
        
        # Write rejected records to CSV
        if self.rejected_records:
            quarantine_file = QUARANTINE_DATA_DIR / "quarantined_rejected_records.csv"
            keys = sorted({k for r in self.rejected_records for k in r.keys()})
            with open(quarantine_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                for row in self.rejected_records:
                    writer.writerow(row)
            print(f"[QUARANTINE] {len(self.rejected_records)} rejected records saved to {quarantine_file}")
