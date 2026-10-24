"""
Fulfillment Analytics and KPI Calculation Engine
Computes Order, Customer, Courier, Fulfillment, and Trend KPIs
"""

from src.database.connection import get_db_connection

class KPICalculator:
    def __init__(self):
        pass

    def get_order_kpis(self) -> dict:
        """Calculates core Order and Fulfillment KPIs."""
        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
        SELECT
            COUNT(*) AS total_orders,
            SUM(DELIVERED_FLAG) AS delivered_orders,
            SUM(CANCELLED_FLAG) AS cancelled_orders,
            SUM(RETURNED_FLAG) AS returned_orders,
            SUM(IN_TRANSIT_FLAG) AS in_transit_orders,
            ROUND(AVG(CASE WHEN DELIVERED_FLAG = 1 THEN DELIVERY_DAYS END), 2) AS avg_delivery_days,
            ROUND(AVG(SLA_DAYS), 2) AS avg_sla_days,
            ROUND(CAST(SUM(ON_TIME_FLAG) AS REAL) / NULLIF(SUM(DELIVERED_FLAG), 0) * 100.0, 2) AS on_time_delivery_pct,
            ROUND(CAST(SUM(LATE_DELIVERY_FLAG) AS REAL) / NULLIF(SUM(DELIVERED_FLAG), 0) * 100.0, 2) AS late_delivery_pct,
            ROUND(CAST(SUM(DELIVERED_FLAG) AS REAL) / COUNT(*) * 100.0, 2) AS shipment_success_rate_pct,
            ROUND(SUM(TOTAL_AMOUNT), 2) AS total_revenue
        FROM FACT_ORDER_FULFILLMENT;
        """
        cursor.execute(query)
        row = cursor.fetchone()
        conn.close()

        return dict(row) if row else {}

    def get_customer_kpis(self) -> dict:
        """Calculates customer metrics and top 10 customers."""
        conn = get_db_connection()
        cursor = conn.cursor()

        # Distinct customers in orders
        cursor.execute("SELECT COUNT(DISTINCT CUSTOMER_KEY) AS distinct_customers FROM FACT_ORDER_FULFILLMENT")
        distinct_cust = cursor.fetchone()["distinct_customers"]

        # Top 10 Customers by Orders
        top_query = """
        SELECT 
            c.CUSTOMER_ID,
            c.CUSTOMER_NAME,
            c.CITY,
            c.CUSTOMER_SEGMENT,
            COUNT(f.ORDER_ID) AS total_orders,
            ROUND(SUM(f.TOTAL_AMOUNT), 2) AS total_spend,
            SUM(f.DELIVERED_FLAG) AS delivered_orders
        FROM FACT_ORDER_FULFILLMENT f
        JOIN DIM_CUSTOMER c ON f.CUSTOMER_KEY = c.CUSTOMER_KEY
        GROUP BY c.CUSTOMER_ID, c.CUSTOMER_NAME, c.CITY, c.CUSTOMER_SEGMENT
        ORDER BY total_orders DESC, total_spend DESC
        LIMIT 10;
        """
        cursor.execute(top_query)
        top_10 = [dict(r) for r in cursor.fetchall()]
        conn.close()

        return {
            "distinct_customers": distinct_cust,
            "top_10_customers": top_10
        }

    def get_courier_kpis(self) -> dict:
        """Calculates courier SLA performance, on-time %, and best/worst rankings."""
        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
        SELECT
            c.COURIER_NAME,
            c.SLA_DAYS,
            c.SERVICE_TYPE,
            c.ACTIVE_FLAG,
            COUNT(f.ORDER_ID) AS total_orders,
            SUM(f.DELIVERED_FLAG) AS delivered_orders,
            SUM(f.ON_TIME_FLAG) AS on_time_orders,
            SUM(f.LATE_DELIVERY_FLAG) AS late_orders,
            ROUND(CAST(SUM(f.ON_TIME_FLAG) AS REAL) / NULLIF(SUM(f.DELIVERED_FLAG), 0) * 100.0, 2) AS on_time_pct,
            ROUND(CAST(SUM(f.LATE_DELIVERY_FLAG) AS REAL) / NULLIF(SUM(f.DELIVERED_FLAG), 0) * 100.0, 2) AS delay_pct,
            ROUND(AVG(CASE WHEN f.DELIVERED_FLAG = 1 THEN f.DELIVERY_DAYS END), 2) AS avg_delivery_days,
            ROUND(AVG(CASE WHEN f.DELIVERED_FLAG = 1 THEN f.DELAY_DAYS END), 2) AS avg_delay_days
        FROM FACT_ORDER_FULFILLMENT f
        JOIN DIM_COURIER c ON f.COURIER_KEY = c.COURIER_KEY
        GROUP BY c.COURIER_NAME, c.SLA_DAYS, c.SERVICE_TYPE, c.ACTIVE_FLAG
        ORDER BY total_orders DESC;
        """
        cursor.execute(query)
        couriers = [dict(r) for r in cursor.fetchall()]
        conn.close()

        # Determine Best and Worst
        valid_delivered = [c for c in couriers if (c["delivered_orders"] or 0) > 0]
        best_courier = max(valid_delivered, key=lambda c: (c["on_time_pct"] or 0)) if valid_delivered else None
        worst_courier = max(valid_delivered, key=lambda c: (c["delay_pct"] or 0)) if valid_delivered else None

        return {
            "courier_metrics": couriers,
            "best_performing_courier": best_courier,
            "worst_performing_courier": worst_courier
        }

    def get_trend_kpis(self) -> dict:
        """Calculates monthly trends for orders, deliveries, and status distributions."""
        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
        SELECT
            SUBSTR(ORDER_DATE, 1, 7) AS year_month,
            COUNT(*) AS total_orders,
            SUM(DELIVERED_FLAG) AS delivered_orders,
            SUM(CANCELLED_FLAG) AS cancelled_orders,
            SUM(RETURNED_FLAG) AS returned_orders,
            SUM(IN_TRANSIT_FLAG) AS in_transit_orders,
            ROUND(AVG(CASE WHEN DELIVERED_FLAG = 1 THEN DELIVERY_DAYS END), 2) AS avg_delivery_days,
            ROUND(SUM(TOTAL_AMOUNT), 2) AS monthly_revenue
        FROM FACT_ORDER_FULFILLMENT
        WHERE ORDER_DATE IS NOT NULL
        GROUP BY SUBSTR(ORDER_DATE, 1, 7)
        ORDER BY year_month ASC;
        """
        cursor.execute(query)
        monthly_trends = [dict(r) for r in cursor.fetchall()]

        # Status distribution
        status_query = """
        SELECT ORDER_STATUS, COUNT(*) AS count, ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM FACT_ORDER_FULFILLMENT), 2) AS pct
        FROM FACT_ORDER_FULFILLMENT
        GROUP BY ORDER_STATUS
        ORDER BY count DESC;
        """
        cursor.execute(status_query)
        status_dist = [dict(r) for r in cursor.fetchall()]

        conn.close()
        return {
            "monthly_trends": monthly_trends,
            "status_distribution": status_dist
        }

    def get_city_kpis(self) -> list:
        """Calculates geographic delivery delay and fulfillment metrics by city."""
        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
        SELECT 
            c.CITY,
            COUNT(f.ORDER_ID) AS total_orders,
            SUM(f.DELIVERED_FLAG) AS delivered_orders,
            SUM(f.LATE_DELIVERY_FLAG) AS late_orders,
            ROUND(CAST(SUM(f.ON_TIME_FLAG) AS REAL) / NULLIF(SUM(f.DELIVERED_FLAG), 0) * 100.0, 2) AS on_time_pct,
            ROUND(CAST(SUM(f.LATE_DELIVERY_FLAG) AS REAL) / NULLIF(SUM(f.DELIVERED_FLAG), 0) * 100.0, 2) AS delay_pct,
            ROUND(AVG(CASE WHEN f.DELIVERED_FLAG = 1 THEN f.DELIVERY_DAYS END), 2) AS avg_delivery_days,
            ROUND(AVG(CASE WHEN f.DELIVERED_FLAG = 1 THEN f.DELAY_DAYS END), 2) AS avg_delay_days
        FROM FACT_ORDER_FULFILLMENT f
        JOIN DIM_CUSTOMER c ON f.CUSTOMER_KEY = c.CUSTOMER_KEY
        WHERE c.CITY IS NOT NULL AND c.CITY != 'UNKNOWN'
        GROUP BY c.CITY
        ORDER BY total_orders DESC
        LIMIT 10;
        """
        cursor.execute(query)
        cities = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return cities

    def get_courier_monthly_trends(self) -> list:
        """Calculates courier-wise monthly trends."""
        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
        SELECT 
            SUBSTR(f.ORDER_DATE, 1, 7) AS year_month,
            c.COURIER_NAME,
            COUNT(f.ORDER_ID) AS total_orders,
            SUM(f.DELIVERED_FLAG) AS delivered_orders,
            ROUND(CAST(SUM(f.ON_TIME_FLAG) AS REAL) / NULLIF(SUM(f.DELIVERED_FLAG), 0) * 100.0, 2) AS on_time_pct
        FROM FACT_ORDER_FULFILLMENT f
        JOIN DIM_COURIER c ON f.COURIER_KEY = c.COURIER_KEY
        WHERE f.ORDER_DATE IS NOT NULL
        GROUP BY SUBSTR(f.ORDER_DATE, 1, 7), c.COURIER_NAME
        ORDER BY year_month ASC, total_orders DESC;
        """
        cursor.execute(query)
        courier_trends = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return courier_trends
