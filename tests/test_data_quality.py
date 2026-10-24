"""
Automated Unit Tests for Data Quality Framework
Verifies validation rules matching assessment requirements
"""

import unittest
from src.data_quality.quarantine import QuarantineManager
from src.data_quality.validator import DataQualityValidator
from src.data_quality.cleaner import parse_date_robust, normalize_status, normalize_courier

class TestDataQualityRules(unittest.TestCase):
    def setUp(self):
        self.qm = QuarantineManager()
        self.mock_courier_master = {
            "Delhivery": {"COURIER_ID": "CR01", "SLA_DAYS": 4, "ACTIVE_FLAG": "Y"},
            "Blue Dart": {"COURIER_ID": "CR02", "SLA_DAYS": 2, "ACTIVE_FLAG": "Y"},
            "Gati": {"COURIER_ID": "CR09", "SLA_DAYS": 6, "ACTIVE_FLAG": "N"},
        }
        self.validator = DataQualityValidator(self.qm, self.mock_courier_master)

    def test_null_customer_id_rejected(self):
        raw = {"CUSTOMER_ID": "", "CUSTOMER_NAME": "John Doe", "CITY": "Mumbai"}
        is_valid, _ = self.validator.validate_customer_record(raw)
        self.assertFalse(is_valid)

    def test_null_customer_name_flagged(self):
        raw = {"CUSTOMER_ID": "C10001", "CUSTOMER_NAME": "", "CITY": "Mumbai"}
        is_valid, cleaned = self.validator.validate_customer_record(raw)
        self.assertTrue(is_valid)
        self.assertEqual(cleaned["CUSTOMER_NAME"], "UNKNOWN")

    def test_invalid_date_quarantined(self):
        raw = {
            "ORDER_ID": "ORD9999", "CUSTOMER_ID": "C10001", "PRODUCT_ID": "P100",
            "QUANTITY": "1", "ORDER_DATE": "2026/13/40", "COURIER_NAME": "Delhivery",
            "ORDER_STATUS": "Delivered", "DELIVERY_DATE": "2026-05-10"
        }
        is_valid, _ = self.validator.validate_order_transaction(raw, "test.csv", {"C10001"}, {})
        self.assertFalse(is_valid)

    def test_negative_quantity_rejected(self):
        raw = {
            "ORDER_ID": "ORD9998", "CUSTOMER_ID": "C10001", "PRODUCT_ID": "P100",
            "QUANTITY": "-5", "ORDER_DATE": "2026-05-01", "COURIER_NAME": "Delhivery",
            "ORDER_STATUS": "Delivered", "DELIVERY_DATE": "2026-05-05"
        }
        is_valid, _ = self.validator.validate_order_transaction(raw, "test.csv", {"C10001"}, {})
        self.assertFalse(is_valid)

    def test_chronology_violation_rejected(self):
        # Delivery before order date
        raw = {
            "ORDER_ID": "ORD9997", "CUSTOMER_ID": "C10001", "PRODUCT_ID": "P100",
            "QUANTITY": "1", "ORDER_DATE": "2026-05-10", "DELIVERY_DATE": "2026-05-05",
            "COURIER_NAME": "Delhivery", "ORDER_STATUS": "Delivered"
        }
        is_valid, _ = self.validator.validate_order_transaction(raw, "test.csv", {"C10001"}, {})
        self.assertFalse(is_valid)

    def test_unknown_courier_rejected(self):
        raw = {
            "ORDER_ID": "ORD9996", "CUSTOMER_ID": "C10001", "PRODUCT_ID": "P100",
            "QUANTITY": "1", "ORDER_DATE": "2026-05-01", "DELIVERY_DATE": "2026-05-05",
            "COURIER_NAME": "Unknown Courier Inc", "ORDER_STATUS": "Delivered"
        }
        is_valid, _ = self.validator.validate_order_transaction(raw, "test.csv", {"C10001"}, {})
        self.assertFalse(is_valid)

    def test_date_parser_supports_multiple_formats(self):
        d1, v1, m1 = parse_date_robust("2026-05-18")
        d2, v2, m2 = parse_date_robust("18-05-2026")
        d3, v3, m3 = parse_date_robust("2026/05/18")
        self.assertEqual(d1, "2026-05-18")
        self.assertEqual(d2, "2026-05-18")
        self.assertEqual(d3, "2026-05-18")

if __name__ == "__main__":
    unittest.main()
