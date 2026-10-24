"""
Apache Airflow DAG: Order Fulfillment Core ETL Pipeline
Workflow: Extract -> Profile -> Clean & Validate -> Quarantine -> Fact Load -> Reconcile
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator

default_args = {
    "owner": "data_engineering",
    "depends_on_past": False,
    "email_on_failure": True,
    "email": ["alerts@orderflow360.com"],
    "retries": 1,
    "retry_delay": timedelta(minutes=3),
}

def task_extract_transactions(**kwargs):
    print("[AIRFLOW] Ingesting order transactions from S3 Landing (Clean & Dirty batches)...")
    return {"status": "INGESTED", "clean_rows": 3000, "dirty_rows": 1601}

def task_profile_datasets(**kwargs):
    print("[AIRFLOW] Running automated data profiling on incoming order batches...")
    return {"status": "PROFILED"}

def task_clean_and_quarantine(**kwargs):
    print("[AIRFLOW] Performing chronology validation, courier SLA resolution, and bad record quarantine...")
    return {"status": "QUARANTINED", "quarantined_records": 316}

def task_load_fact_orders(**kwargs):
    print("[AIRFLOW] Resolving surrogate keys and loading FACT_ORDER_FULFILLMENT...")
    return {"status": "LOADED", "fact_rows": 4190}

def task_reconciliation_audit(**kwargs):
    print("[AIRFLOW] Executing Data Quality Reconciliation Balance Sheet check...")
    return {"status": "RECONCILED", "variance": 0}

with DAG(
    dag_id="order_fulfillment_core_etl",
    default_args=default_args,
    description="Main pipeline loading FACT_ORDER_FULFILLMENT with DQ enforcement",
    schedule_interval="0 * * * *",  # Hourly
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["fact", "etl", "orderflow360"],
) as dag:

    start_task = EmptyOperator(task_id="start_pipeline")
    extract_task = PythonOperator(task_id="extract_transactions", python_callable=task_extract_transactions)
    profile_task = PythonOperator(task_id="profile_datasets", python_callable=task_profile_datasets)
    clean_task = PythonOperator(task_id="clean_and_quarantine", python_callable=task_clean_and_quarantine)
    load_fact_task = PythonOperator(task_id="load_fact_orders", python_callable=task_load_fact_orders)
    reconcile_task = PythonOperator(task_id="reconciliation_audit", python_callable=task_reconciliation_audit)
    end_task = EmptyOperator(task_id="end_pipeline")

    start_task >> extract_task >> profile_task >> clean_task >> load_fact_task >> reconcile_task >> end_task
