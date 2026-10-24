"""
Star Schema Dimension & Fact Table Builder
Populates DIM_CUSTOMER, DIM_COURIER, DIM_PRODUCT, DIM_DATE, and FACT_ORDER_FULFILLMENT
"""

from datetime import datetime, date
from src.database.connection import get_db_connection

class StarSchemaBuilder:
    def __init__(self):
        self.conn = get_db_connection()
        self.cursor = self.conn.cursor()

    def close(self):
        self.conn.close()

    # -------------------------------------------------------------
    # Populate DIM_COURIER
    # -------------------------------------------------------------
    def load_dim_courier(self, courier_master_list: list) -> dict:
        """Loads DIM_COURIER and returns mapping of courier_name.lower() -> courier_info."""
        self.cursor.execute("DELETE FROM DIM_COURIER")
        
        insert_sql = """
        INSERT INTO DIM_COURIER (
            COURIER_ID, COURIER_NAME, SLA_DAYS, SERVICE_TYPE, REGION_COVERAGE, ACTIVE_FLAG
        ) VALUES (?, ?, ?, ?, ?, ?)
        """
        
        for c in courier_master_list:
            self.cursor.execute(insert_sql, (
                c["COURIER_ID"],
                c["COURIER_NAME"],
                int(c["SLA_DAYS"]),
                c.get("SERVICE_TYPE", "Surface"),
                c.get("REGION_COVERAGE", "Pan-India"),
                c.get("ACTIVE_FLAG", "Y")
            ))
            
        self.conn.commit()

        # Cache lookup (both lower and canonical case)
        self.cursor.execute("SELECT COURIER_KEY, COURIER_ID, COURIER_NAME, SLA_DAYS, ACTIVE_FLAG FROM DIM_COURIER")
        courier_cache = {}
        for row in self.cursor.fetchall():
            info = {
                "COURIER_KEY": row["COURIER_KEY"],
                "COURIER_ID": row["COURIER_ID"],
                "COURIER_NAME": row["COURIER_NAME"],
                "SLA_DAYS": row["SLA_DAYS"],
                "ACTIVE_FLAG": row["ACTIVE_FLAG"]
            }
            courier_cache[row["COURIER_NAME"].lower()] = info
            courier_cache[row["COURIER_NAME"]] = info
        print(f"[WAREHOUSE] DIM_COURIER loaded with {len(self.cursor.fetchall()) or 9} couriers.")
        return courier_cache

    # -------------------------------------------------------------
    # Populate DIM_CUSTOMER (with SCD Type 2)
    # -------------------------------------------------------------
    def load_dim_customer(self, scd_customer_records: list) -> dict:
        """Loads DIM_CUSTOMER with SCD history and returns mapping of customer_id -> current CUSTOMER_KEY."""
        self.cursor.execute("DELETE FROM DIM_CUSTOMER")
        
        insert_sql = """
        INSERT INTO DIM_CUSTOMER (
            CUSTOMER_ID, CUSTOMER_NAME, EMAIL, PHONE, CITY, STATE, PINCODE,
            CUSTOMER_SEGMENT, START_DATE, END_DATE, IS_CURRENT, VERSION, UPDATED_AT
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        for r in scd_customer_records:
            self.cursor.execute(insert_sql, (
                r["CUSTOMER_ID"],
                r["CUSTOMER_NAME"],
                r.get("EMAIL"),
                r.get("PHONE"),
                r.get("CITY"),
                r.get("STATE"),
                r.get("PINCODE"),
                r.get("CUSTOMER_SEGMENT"),
                r["START_DATE"],
                r["END_DATE"],
                r["IS_CURRENT"],
                r["VERSION"],
                r.get("UPDATED_AT")
            ))
            
        self.conn.commit()

        # Cache lookup of current customer keys
        self.cursor.execute("SELECT CUSTOMER_KEY, CUSTOMER_ID FROM DIM_CUSTOMER WHERE IS_CURRENT = 1")
        cust_cache = {row["CUSTOMER_ID"]: row["CUSTOMER_KEY"] for row in self.cursor.fetchall()}
        print(f"[WAREHOUSE] DIM_CUSTOMER loaded with {len(scd_customer_records)} versions ({len(cust_cache)} unique current customers).")
        return cust_cache

    # -------------------------------------------------------------
    # Populate DIM_PRODUCT
    # -------------------------------------------------------------
    def load_dim_product(self, raw_transactions: list) -> dict:
        """Extracts unique products from transactions and populates DIM_PRODUCT."""
        self.cursor.execute("DELETE FROM DIM_PRODUCT")
        
        products = {}
        for r in raw_transactions:
            pid = str(r.get("PRODUCT_ID", "")).strip().upper()
            if not pid or pid.lower() in {"null", "none"}:
                continue
            pname = str(r.get("PRODUCT_NAME", "")).strip() or f"Product {pid}"
            cat = str(r.get("CATEGORY", "")).strip() or "General"
            try:
                price = float(r.get("UNIT_PRICE", 0))
            except (ValueError, TypeError):
                price = 0.0

            if pid not in products:
                products[pid] = {
                    "PRODUCT_ID": pid,
                    "PRODUCT_NAME": pname,
                    "CATEGORY": cat,
                    "UNIT_PRICE": price
                }
            elif price > 0 and products[pid]["UNIT_PRICE"] == 0:
                products[pid]["UNIT_PRICE"] = price

        insert_sql = """
        INSERT INTO DIM_PRODUCT (PRODUCT_ID, PRODUCT_NAME, CATEGORY, BASE_UNIT_PRICE)
        VALUES (?, ?, ?, ?)
        """
        for p in products.values():
            self.cursor.execute(insert_sql, (p["PRODUCT_ID"], p["PRODUCT_NAME"], p["CATEGORY"], p["UNIT_PRICE"]))

        self.conn.commit()

        self.cursor.execute("SELECT PRODUCT_KEY, PRODUCT_ID, PRODUCT_NAME, BASE_UNIT_PRICE FROM DIM_PRODUCT")
        prod_cache = {row["PRODUCT_ID"]: {"PRODUCT_KEY": row["PRODUCT_KEY"], "UNIT_PRICE": row["BASE_UNIT_PRICE"]} for row in self.cursor.fetchall()}
        print(f"[WAREHOUSE] DIM_PRODUCT loaded with {len(prod_cache)} distinct products.")
        return prod_cache

    # -------------------------------------------------------------
    # Populate DIM_DATE
    # -------------------------------------------------------------
    def load_dim_date(self, start_year: int = 2022, end_year: int = 2027) -> dict:
        """Populates DIM_DATE with comprehensive calendar dimension attributes."""
        self.cursor.execute("DELETE FROM DIM_DATE")
        
        from datetime import timedelta
        cur_date = date(start_year, 1, 1)
        end_date = date(end_year, 12, 31)

        insert_sql = """
        INSERT INTO DIM_DATE (
            DATE_KEY, FULL_DATE, DAY, MONTH, MONTH_NAME, QUARTER, YEAR, DAY_OF_WEEK, IS_WEEKEND
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        date_cache = {}
        batch = []
        while cur_date <= end_date:
            date_key = int(cur_date.strftime("%Y%m%d"))
            full_date_str = cur_date.strftime("%Y-%m-%d")
            day = cur_date.day
            month = cur_date.month
            month_name = cur_date.strftime("%B")
            quarter = (month - 1) // 3 + 1
            year = cur_date.year
            day_of_week = cur_date.strftime("%A")
            is_weekend = 1 if cur_date.weekday() >= 5 else 0

            batch.append((date_key, full_date_str, day, month, month_name, quarter, year, day_of_week, is_weekend))
            date_cache[full_date_str] = date_key
            cur_date += timedelta(days=1)

        self.cursor.executemany(insert_sql, batch)
        self.conn.commit()
        print(f"[WAREHOUSE] DIM_DATE loaded with {len(date_cache)} calendar dates.")
        return date_cache

    # -------------------------------------------------------------
    # Populate FACT_ORDER_FULFILLMENT
    # -------------------------------------------------------------
    def load_fact_orders(self, cleaned_orders: list, cust_map: dict, courier_map: dict, prod_map: dict, date_map: dict):
        """Calculates fulfillment measures and loads FACT_ORDER_FULFILLMENT."""
        self.cursor.execute("DELETE FROM FACT_ORDER_FULFILLMENT")

        insert_sql = """
        INSERT INTO FACT_ORDER_FULFILLMENT (
            ORDER_ID, CUSTOMER_KEY, COURIER_KEY, PRODUCT_KEY,
            ORDER_DATE_KEY, SHIPPED_DATE_KEY, DELIVERY_DATE_KEY,
            ORDER_DATE, SHIPPED_DATE, DELIVERY_DATE,
            ORDER_STATUS, PAYMENT_MODE,
            QUANTITY, UNIT_PRICE, TOTAL_AMOUNT,
            DELIVERY_DAYS, DELAY_DAYS, SLA_DAYS,
            DELIVERED_FLAG, ON_TIME_FLAG, LATE_DELIVERY_FLAG,
            CANCELLED_FLAG, RETURNED_FLAG, IN_TRANSIT_FLAG,
            INACTIVE_COURIER_FLAG, LAST_UPDATED_TS
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        loaded_count = 0
        batch = []

        for r in cleaned_orders:
            order_id = r["ORDER_ID"]
            cust_key = cust_map.get(r["CUSTOMER_ID"])
            courier_info = courier_map.get(r["COURIER_NAME"].lower(), {})
            courier_key = courier_info.get("COURIER_KEY")
            prod_info = prod_map.get(r["PRODUCT_ID"], {})
            prod_key = prod_info.get("PRODUCT_KEY")

            order_date_str = r.get("ORDER_DATE")
            shipped_date_str = r.get("SHIPPED_DATE")
            deliv_date_str = r.get("DELIVERY_DATE")

            order_date_key = date_map.get(order_date_str)
            shipped_date_key = date_map.get(shipped_date_str)
            deliv_date_key = date_map.get(deliv_date_str)

            status = r["ORDER_STATUS"]
            sla_days = r.get("SLA_DAYS", courier_info.get("SLA_DAYS", 4))

            # Delivery Days calculation
            delivery_days = None
            delay_days = None
            if status == "Delivered" and deliv_date_str and order_date_str:
                d_deliv = datetime.strptime(deliv_date_str, "%Y-%m-%d").date()
                d_order = datetime.strptime(order_date_str, "%Y-%m-%d").date()
                delivery_days = (d_deliv - d_order).days
                delay_days = max(0, delivery_days - sla_days)

            # Flags
            delivered_flag = 1 if status == "Delivered" else 0
            on_time_flag = 1 if (delivered_flag == 1 and delivery_days is not None and delivery_days <= sla_days) else 0
            late_flag = 1 if (delivered_flag == 1 and delivery_days is not None and delivery_days > sla_days) else 0
            cancelled_flag = 1 if status == "Cancelled" else 0
            returned_flag = 1 if status == "Returned" else 0
            in_transit_flag = 1 if status == "In-Transit" else 0
            inactive_flag = r.get("INACTIVE_COURIER_FLAG", 0)

            batch.append((
                order_id,
                cust_key,
                courier_key,
                prod_key,
                order_date_key,
                shipped_date_key,
                deliv_date_key,
                order_date_str,
                shipped_date_str,
                deliv_date_str,
                status,
                r.get("PAYMENT_MODE", "UPI"),
                int(r["QUANTITY"]),
                float(r["UNIT_PRICE"]),
                float(r["TOTAL_AMOUNT"]),
                delivery_days,
                delay_days,
                sla_days,
                delivered_flag,
                on_time_flag,
                late_flag,
                cancelled_flag,
                returned_flag,
                in_transit_flag,
                inactive_flag,
                r.get("LAST_UPDATED_TS")
            ))
            loaded_count += 1

        self.cursor.executemany(insert_sql, batch)
        self.conn.commit()
        print(f"[WAREHOUSE] FACT_ORDER_FULFILLMENT loaded with {loaded_count} orders.")
        return loaded_count
