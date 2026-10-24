"""
Master ETL Pipeline Orchestrator
Executes the end-to-end data pipeline from raw landing to Curated Star Schema and KPI outputs
"""

import csv
import sys
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (
    SOURCE_CUSTOMER_MASTER,
    SOURCE_ORDER_TRANSACTIONS,
    SOURCE_ORDER_TRANSACTIONS_DIRTY,
    SOURCE_COURIER_SLA,
    REPORTS_DIR
)
from src.database.ddl import init_database
from src.data_quality.profiler import DataProfiler
from src.data_quality.quarantine import QuarantineManager
from src.data_quality.validator import DataQualityValidator
from src.etl.cdc_scd import CDCSCDProcessor
from src.etl.star_schema_builder import StarSchemaBuilder
from src.analytics.kpi_calculator import KPICalculator
from src.analytics.reconciliation import ReconciliationEngine

class OrderFlow360Pipeline:
    def __init__(self):
        self.qm = QuarantineManager()
        self.profiler = DataProfiler()
        self.schema_builder = StarSchemaBuilder()
        self.cdcscd = CDCSCDProcessor(self.qm)
        self.kpi_calc = KPICalculator()
        self.reconciliation = ReconciliationEngine()

    def run_pipeline(self) -> dict:
        print("\n" + "="*60)
        print("  STARTING ORDERFLOW360 DATA ENGINEERING ETL PIPELINE")
        print("="*60 + "\n")

        # -------------------------------------------------------------
        # Step 1: Data Profiling
        # -------------------------------------------------------------
        print("[STEP 1/9] Profiling incoming datasets...")
        self.profiler.profile_file(SOURCE_CUSTOMER_MASTER, primary_key="CUSTOMER_ID")
        self.profiler.profile_file(SOURCE_ORDER_TRANSACTIONS, primary_key="ORDER_ID")
        self.profiler.profile_file(SOURCE_ORDER_TRANSACTIONS_DIRTY, primary_key="ORDER_ID")
        self.profiler.profile_file(SOURCE_COURIER_SLA, primary_key="COURIER_ID")
        
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        profiling_report_path = REPORTS_DIR / "data_profiling_report.md"
        with open(profiling_report_path, "w", encoding="utf-8") as f:
            f.write(self.profiler.generate_markdown_report())
        print(f"[PROFILER] Profiling complete. Report saved: {profiling_report_path}")

        # -------------------------------------------------------------
        # Step 2: Initialize Database Schema
        # -------------------------------------------------------------
        print("\n[STEP 2/9] Initializing Warehouse Star Schema and Audit Tables...")
        init_database()

        # -------------------------------------------------------------
        # Step 3: Load Courier Dimension
        # -------------------------------------------------------------
        print("\n[STEP 3/9] Ingesting and Loading DIM_COURIER...")
        couriers_raw = []
        with open(SOURCE_COURIER_SLA, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                couriers_raw.append(row)

        courier_cache = self.schema_builder.load_dim_courier(couriers_raw)

        # -------------------------------------------------------------
        # Step 4: Validate Customer Master & Build SCD DIM_CUSTOMER
        # -------------------------------------------------------------
        print("\n[STEP 4/9] Validating Customers and Processing SCD Type 1 & 2...")
        validator = DataQualityValidator(self.qm, courier_cache)
        
        valid_customers = []
        raw_cust_count = 0
        with open(SOURCE_CUSTOMER_MASTER, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                raw_cust_count += 1
                is_valid, cleaned_row = validator.validate_customer_record(row)
                if is_valid and cleaned_row:
                    valid_customers.append(cleaned_row)

        dim_cust_records = self.cdcscd.process_customer_scd(valid_customers)
        cust_cache = self.schema_builder.load_dim_customer(dim_cust_records)
        valid_cust_ids = set(cust_cache.keys())

        # -------------------------------------------------------------
        # Step 5: Ingest Transactions, Load DIM_PRODUCT & DIM_DATE
        # -------------------------------------------------------------
        print("\n[STEP 5/9] Loading DIM_PRODUCT and DIM_DATE...")
        raw_clean_orders = []
        raw_dirty_orders = []

        with open(SOURCE_ORDER_TRANSACTIONS, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                raw_clean_orders.append(row)

        with open(SOURCE_ORDER_TRANSACTIONS_DIRTY, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                raw_dirty_orders.append(row)

        all_raw_orders = raw_clean_orders + raw_dirty_orders
        prod_cache = self.schema_builder.load_dim_product(all_raw_orders)
        date_cache = self.schema_builder.load_dim_date(start_year=2022, end_year=2027)

        # -------------------------------------------------------------
        # Step 6: CDC & Transaction Upsert Resolution
        # -------------------------------------------------------------
        print("\n[STEP 6/9] Processing Transaction CDC, Cross-File Upserts & Conflicting Duplicates...")
        batches = [
            ("order_transactions_v3.csv", raw_clean_orders),
            ("order_transactions_dirty_v3.csv", raw_dirty_orders)
        ]
        cdc_resolved_orders = self.cdcscd.process_order_cdc(batches)
        print(f"[CDC] Total CDC candidates after deduplication: {len(cdc_resolved_orders)}")

        # -------------------------------------------------------------
        # Step 7: Validate Transactions & Segregate Bad Records
        # -------------------------------------------------------------
        print("\n[STEP 7/9] Validating Transactions, Chronology, SLA Couriers, and Quantities...")
        cleaned_valid_orders = []
        for r in cdc_resolved_orders:
            src_file = r.get("_SOURCE_FILE", "order_transactions_dirty_v3.csv")
            is_valid, cleaned_row = validator.validate_order_transaction(
                r,
                source_file=src_file,
                valid_cust_ids=valid_cust_ids,
                product_catalog=prod_cache
            )
            if is_valid and cleaned_row:
                cleaned_valid_orders.append(cleaned_row)

        print(f"[VALIDATION] Passed: {len(cleaned_valid_orders)} orders. Bad/Quarantined segregated.")

        # -------------------------------------------------------------
        # Step 8: Load FACT_ORDER_FULFILLMENT & Persist Quarantine
        # -------------------------------------------------------------
        print("\n[STEP 8/9] Loading FACT_ORDER_FULFILLMENT and Persisting Audit Logs...")
        loaded_fact_count = self.schema_builder.load_fact_orders(
            cleaned_orders=cleaned_valid_orders,
            cust_map=cust_cache,
            courier_map=courier_cache,
            prod_map=prod_cache,
            date_map=date_cache
        )
        self.qm.persist()

        # -------------------------------------------------------------
        # Step 9: Calculate KPIs and Run Reconciliation
        # -------------------------------------------------------------
        print("\n[STEP 9/9] Calculating KPIs and Generating Data Reconciliation Audit...")
        order_kpis = self.kpi_calc.get_order_kpis()
        cust_kpis = self.kpi_calc.get_customer_kpis()
        courier_kpis = self.kpi_calc.get_courier_kpis()
        trend_kpis = self.kpi_calc.get_trend_kpis()

        raw_counts = {
            "customer_raw_count": raw_cust_count,
            "courier_raw_count": len(couriers_raw),
            "order_clean_count": len(raw_clean_orders),
            "order_dirty_count": len(raw_dirty_orders),
        }
        reconciliation_summary = self.reconciliation.run_reconciliation(raw_counts)

        print("\n" + "="*60)
        print("  ETL PIPELINE EXECUTION COMPLETED SUCCESSFULLY!")
        print("="*60)
        print(f"- Total Orders Loaded to Warehouse: {loaded_fact_count:,}")
        print(f"- On-Time Delivery Rate: {order_kpis.get('on_time_delivery_pct')}%")
        print(f"- Average Delivery Days: {order_kpis.get('avg_delivery_days')} days")
        print(f"- Total Quarantined Records: {len(self.qm.rejected_records):,}")
        print(f"- DQ Issues Logged to Audit Table: {len(self.qm.audit_entries):,}")
        print("="*60 + "\n")

        return {
            "status": "SUCCESS",
            "fact_orders_loaded": loaded_fact_count,
            "order_kpis": order_kpis,
            "courier_kpis": courier_kpis,
            "reconciliation": reconciliation_summary
        }

if __name__ == "__main__":
    pipeline = OrderFlow360Pipeline()
    pipeline.run_pipeline()
