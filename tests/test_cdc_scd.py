"""
Automated Unit Tests for CDC & SCD Processing
Verifies SCD Type 1 & Type 2 transitions and CDC Upsert logic
"""

import unittest
from src.data_quality.quarantine import QuarantineManager
from src.etl.cdc_scd import CDCSCDProcessor

class TestCDCSCDLogic(unittest.TestCase):
    def setUp(self):
        self.qm = QuarantineManager()
        self.processor = CDCSCDProcessor(self.qm)

    def test_scd2_address_change(self):
        records = [
            {
                "CUSTOMER_ID": "C10001", "CUSTOMER_NAME": "Alice", "EMAIL": "alice@test.com",
                "PHONE": "9876543210", "CITY": "Mumbai", "STATE": "Maharashtra", "PINCODE": "400001",
                "CUSTOMER_SEGMENT": "Regular", "LAST_UPDATED_TS": "2025-01-01 10:00:00"
            },
            {
                "CUSTOMER_ID": "C10001", "CUSTOMER_NAME": "Alice", "EMAIL": "alice@test.com",
                "PHONE": "9876543210", "CITY": "Pune", "STATE": "Maharashtra", "PINCODE": "411001",
                "CUSTOMER_SEGMENT": "Regular", "LAST_UPDATED_TS": "2026-02-01 12:00:00"
            }
        ]
        scd_history = self.processor.process_customer_scd(records)
        self.assertEqual(len(scd_history), 2)
        
        # Version 1 should be closed
        v1 = scd_history[0]
        self.assertEqual(v1["CITY"], "Mumbai")
        self.assertEqual(v1["IS_CURRENT"], 0)
        self.assertEqual(v1["END_DATE"], "2026-02-01 12:00:00")
        
        # Version 2 should be active
        v2 = scd_history[1]
        self.assertEqual(v2["CITY"], "Pune")
        self.assertEqual(v2["IS_CURRENT"], 1)
        self.assertEqual(v2["END_DATE"], "9999-12-31 00:00:00")
        self.assertEqual(v2["VERSION"], 2)

    def test_scd1_segment_update(self):
        records = [
            {
                "CUSTOMER_ID": "C10002", "CUSTOMER_NAME": "Bob", "EMAIL": "bob@test.com",
                "PHONE": "9876543211", "CITY": "Delhi", "STATE": "Delhi", "PINCODE": "110001",
                "CUSTOMER_SEGMENT": "Regular", "LAST_UPDATED_TS": "2025-01-01 10:00:00"
            },
            {
                "CUSTOMER_ID": "C10002", "CUSTOMER_NAME": "Bob", "EMAIL": "bob@test.com",
                "PHONE": "9876543211", "CITY": "Delhi", "STATE": "Delhi", "PINCODE": "110001",
                "CUSTOMER_SEGMENT": "Premium", "LAST_UPDATED_TS": "2026-03-01 15:00:00"
            }
        ]
        scd_history = self.processor.process_customer_scd(records)
        self.assertEqual(len(scd_history), 1)
        self.assertEqual(scd_history[0]["CUSTOMER_SEGMENT"], "Premium")

    def test_cdc_upsert_picks_latest_timestamp(self):
        batches = [
            ("clean.csv", [
                {"ORDER_ID": "ORD100", "ORDER_STATUS": "In-Transit", "LAST_UPDATED_TS": "2026-05-01 10:00:00"}
            ]),
            ("dirty.csv", [
                {"ORDER_ID": "ORD100", "ORDER_STATUS": "Delivered", "LAST_UPDATED_TS": "2026-05-03 14:00:00"}
            ])
        ]
        resolved = self.processor.process_order_cdc(batches)
        self.assertEqual(len(resolved), 1)
        self.assertEqual(resolved[0]["ORDER_STATUS"], "Delivered")
        self.assertEqual(resolved[0]["LAST_UPDATED_TS"], "2026-05-03 14:00:00")

if __name__ == "__main__":
    unittest.main()
