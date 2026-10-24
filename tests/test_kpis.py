"""
Automated Unit Tests for Fulfillment Analytics & KPI Formulas
Verifies accuracy of business metric calculations
"""

import unittest
from src.analytics.kpi_calculator import KPICalculator

class TestKPIFormulas(unittest.TestCase):
    def setUp(self):
        self.kpi_calc = KPICalculator()

    def test_order_kpi_consistency(self):
        order_kpis = self.kpi_calc.get_order_kpis()
        total = order_kpis.get("total_orders", 0)
        self.assertGreater(total, 0)
        
        delivered = order_kpis.get("delivered_orders", 0)
        cancelled = order_kpis.get("cancelled_orders", 0)
        returned = order_kpis.get("returned_orders", 0)
        in_transit = order_kpis.get("in_transit_orders", 0)
        
        # Total orders must match sum of all canonical order statuses
        self.assertEqual(total, delivered + cancelled + returned + in_transit)

    def test_on_time_rate_bounds(self):
        order_kpis = self.kpi_calc.get_order_kpis()
        on_time_pct = order_kpis.get("on_time_delivery_pct", 0)
        late_pct = order_kpis.get("late_delivery_pct", 0)
        
        self.assertGreaterEqual(on_time_pct, 0.0)
        self.assertLessEqual(on_time_pct, 100.0)
        self.assertAlmostEqual(on_time_pct + late_pct, 100.0, places=1)

    def test_courier_rankings_exist(self):
        courier_data = self.kpi_calc.get_courier_kpis()
        self.assertIsNotNone(courier_data.get("best_performing_courier"))
        self.assertIsNotNone(courier_data.get("worst_performing_courier"))
        self.assertGreater(len(courier_data.get("courier_metrics", [])), 0)

if __name__ == "__main__":
    unittest.main()
