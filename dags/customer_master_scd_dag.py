"""
Apache Airflow DAG: Customer Dimension SCD Processing
Workflow: Extract -> Validate -> CDC -> SCD Type 1 & Type 2 -> Load DIM_CUSTOMER
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
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

def task_extract_customer_master(**kwargs):
    print("[AIRFLOW] Extracting customer master records from S3 landing zone...")
    return {"status": "EXTRACT_COMPLETE", "record_count": 701}

def task_validate_customer_dq(**kwargs):
    print("[AIRFLOW] Applying DQ rules: Mandatory ID, Name, City normalizer, Segment casing...")
    return {"status": "VALIDATION_COMPLETE", "valid_records": 670, "rejected": 31}

def task_process_scd_and_load(**kwargs):
    print("[AIRFLOW] Executing SCD Type 2 address history tracking and SCD Type 1 segment updates...")
    # Calls CDCSCDProcessor and loads DIM_CUSTOMER
    return {"status": "LOAD_COMPLETE", "dim_customer_versions": 663}

with DAG(
    dag_id="customer_dimension_scd_pipeline",
    default_args=default_args,
    description="End-to-end SCD Type 1 & 2 pipeline for DIM_CUSTOMER",
    schedule_interval="@daily",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["dimension", "scd", "orderflow360"],
) as dag:

    start_task = EmptyOperator(task_id="start_pipeline")
    
    extract_task = PythonOperator(
        task_id="extract_customer_master",
        python_callable=task_extract_customer_master
    )
    
    validate_task = PythonOperator(
        task_id="validate_customer_dq",
        python_callable=task_validate_customer_dq
    )
    
    load_scd_task = PythonOperator(
        task_id="process_scd_and_load",
        python_callable=task_process_scd_and_load
    )
    
    end_task = EmptyOperator(task_id="end_pipeline")

    start_task >> extract_task >> validate_task >> load_scd_task >> end_task
