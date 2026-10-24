"""
Apache Airflow DAG: Executive KPI & Courier SLA Reporting
Workflow: Aggregate KPIs -> Populate Daily Snapshot -> Refresh Dashboards -> Alert on SLA breaches
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator

default_args = {
    "owner": "bi_analytics",
    "depends_on_past": False,
    "email_on_failure": True,
    "email": ["alerts@orderflow360.com"],
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

def task_aggregate_fulfillment_kpis(**kwargs):
    print("[AIRFLOW] Calculating Order, Customer, Courier, and Trend KPIs...")
    return {"status": "KPIS_CALCULATED"}

def task_refresh_snapshots(**kwargs):
    print("[AIRFLOW] Upserting daily aggregated KPI snapshot table in warehouse...")
    return {"status": "SNAPSHOT_UPDATED"}

def task_check_sla_alerts(**kwargs):
    print("[AIRFLOW] Checking SLA violations... Alerting management if On-Time % falls below 80% threshold.")
    return {"status": "ALERT_CHECKED"}

with DAG(
    dag_id="kpi_reporting_and_sla_alerts",
    default_args=default_args,
    description="Refreshes KPI tables and triggers alerts for SLA delays",
    schedule_interval="0 6 * * *",  # Every morning at 6 AM
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["reporting", "kpi", "bi"],
) as dag:

    start_task = EmptyOperator(task_id="start_reporting")
    agg_task = PythonOperator(task_id="aggregate_fulfillment_kpis", python_callable=task_aggregate_fulfillment_kpis)
    snapshot_task = PythonOperator(task_id="refresh_snapshots", python_callable=task_refresh_snapshots)
    alert_task = PythonOperator(task_id="check_sla_alerts", python_callable=task_check_sla_alerts)
    end_task = EmptyOperator(task_id="end_reporting")

    start_task >> agg_task >> snapshot_task >> alert_task >> end_task
