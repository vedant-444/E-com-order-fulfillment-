"""
Change Data Capture (CDC) and Slowly Changing Dimensions (SCD) Engine
Handles SCD Type 1 & 2 for Customers, and Timestamp-based Upsert / Conflict Quarantine for Orders
"""

from collections import defaultdict
from datetime import datetime
from src.data_quality.quarantine import QuarantineManager

class CDCSCDProcessor:
    def __init__(self, quarantine_mgr: QuarantineManager):
        self.qm = quarantine_mgr

    # -------------------------------------------------------------
    # Customer SCD Processing (Type 1 for Segment, Type 2 for Address)
    # -------------------------------------------------------------
    def process_customer_scd(self, valid_customer_records: list) -> list:
        """
        Processes cleaned customer records:
        - Deduplicates exact duplicate rows
        - Tracks history with SCD Type 2 for Address changes (CITY, STATE, PINCODE)
        - Updates in-place with SCD Type 1 for Customer Segment changes
        Returns list of customer dimension rows ready for DIM_CUSTOMER.
        """
        by_customer = defaultdict(list)
        seen_exact = set()
        deduped_records = []

        # 1. Exact Duplicate Elimination
        for row in valid_customer_records:
            signature = (
                row["CUSTOMER_ID"],
                row.get("CUSTOMER_NAME"),
                row.get("EMAIL"),
                row.get("PHONE"),
                row.get("CITY"),
                row.get("STATE"),
                row.get("PINCODE"),
                row.get("CUSTOMER_SEGMENT"),
                row.get("LAST_UPDATED_TS")
            )
            if signature in seen_exact:
                self.qm.log_issue(
                    file_name="customer_master_orders_v3.csv",
                    record_key=row["CUSTOMER_ID"],
                    rule_name="EXACT_DUPLICATE_ROW",
                    severity="TRANSFORM",
                    action_taken="DEDUP",
                    error_message=f"Deduplicated identical row for customer {row['CUSTOMER_ID']}",
                    raw_payload=row
                )
            else:
                seen_exact.add(signature)
                deduped_records.append(row)
                by_customer[row["CUSTOMER_ID"]].append(row)

        dim_customer_rows = []

        # 2. SCD Type 1 & Type 2 Transitions
        for cust_id, records in by_customer.items():
            # Sort by LAST_UPDATED_TS ascending
            records.sort(key=lambda r: str(r.get("LAST_UPDATED_TS") or r.get("REGISTRATION_DATE") or "1970-01-01"))
            
            scd_history = []
            
            for i, rec in enumerate(records):
                ts = str(rec.get("LAST_UPDATED_TS") or rec.get("REGISTRATION_DATE") or "2024-01-01 00:00:00")
                
                if i == 0:
                    # Initial record
                    scd_row = {
                        "CUSTOMER_ID": cust_id,
                        "CUSTOMER_NAME": rec["CUSTOMER_NAME"],
                        "EMAIL": rec["EMAIL"],
                        "PHONE": rec["PHONE"],
                        "CITY": rec["CITY"],
                        "STATE": rec["STATE"],
                        "PINCODE": rec["PINCODE"],
                        "CUSTOMER_SEGMENT": rec["CUSTOMER_SEGMENT"],
                        "START_DATE": ts,
                        "END_DATE": "9999-12-31 00:00:00",
                        "IS_CURRENT": 1,
                        "VERSION": 1,
                        "UPDATED_AT": ts
                    }
                    scd_history.append(scd_row)
                else:
                    prev_row = scd_history[-1]
                    
                    # Detect Address Change (SCD Type 2)
                    address_changed = (
                        rec.get("CITY") != prev_row["CITY"] or
                        rec.get("STATE") != prev_row["STATE"] or
                        rec.get("PINCODE") != prev_row["PINCODE"]
                    )
                    
                    # Detect Segment Change (SCD Type 1)
                    segment_changed = (rec.get("CUSTOMER_SEGMENT") != prev_row["CUSTOMER_SEGMENT"])
                    
                    if address_changed:
                        # Close previous record
                        prev_row["END_DATE"] = ts
                        prev_row["IS_CURRENT"] = 0
                        
                        # Open new record version
                        new_row = {
                            "CUSTOMER_ID": cust_id,
                            "CUSTOMER_NAME": rec["CUSTOMER_NAME"],
                            "EMAIL": rec["EMAIL"] or prev_row["EMAIL"],
                            "PHONE": rec["PHONE"] or prev_row["PHONE"],
                            "CITY": rec["CITY"],
                            "STATE": rec["STATE"],
                            "PINCODE": rec["PINCODE"],
                            "CUSTOMER_SEGMENT": rec["CUSTOMER_SEGMENT"],
                            "START_DATE": ts,
                            "END_DATE": "9999-12-31 00:00:00",
                            "IS_CURRENT": 1,
                            "VERSION": prev_row["VERSION"] + 1,
                            "UPDATED_AT": ts
                        }
                        scd_history.append(new_row)
                        
                        self.qm.log_issue(
                            file_name="customer_master_orders_v3.csv",
                            record_key=cust_id,
                            rule_name="ADDRESS_CHANGE_NEW_VERSION",
                            severity="TRANSFORM",
                            action_taken="SCD2: close old row, insert new current row",
                            error_message=f"Customer address changed from {prev_row['CITY']} to {rec['CITY']}; created Version {new_row['VERSION']}",
                            raw_payload=rec
                        )

                    if segment_changed:
                        target_row = scd_history[-1]
                        target_row["CUSTOMER_SEGMENT"] = rec["CUSTOMER_SEGMENT"]
                        target_row["UPDATED_AT"] = ts
                        
                        self.qm.log_issue(
                            file_name="customer_master_orders_v3.csv",
                            record_key=cust_id,
                            rule_name="SEGMENT_CHANGE_NEW_VERSION",
                            severity="TRANSFORM",
                            action_taken="SCD1 overwrite (or SCD2 if you choose)",
                            error_message=f"Segment updated in-place to {rec['CUSTOMER_SEGMENT']}",
                            raw_payload=rec
                        )

            dim_customer_rows.extend(scd_history)

        return dim_customer_rows

    # -------------------------------------------------------------
    # Order Transactions CDC & Duplicate Resolution
    # -------------------------------------------------------------
    def process_order_cdc(self, raw_order_batches: list) -> list:
        """
        raw_order_batches: list of tuples (source_file, list_of_raw_rows)
        Handles:
        1. Exact duplicate rows -> DEDUP
        2. Conflicting duplicates with identical timestamp -> QUARANTINE
        3. CDC updates (same ID different TS or cross-file) -> KEEP LATEST by LAST_UPDATED_TS
        """
        all_rows = []
        for src_file, rows in raw_order_batches:
            for r in rows:
                r["_SOURCE_FILE"] = src_file
                all_rows.append(r)

        # 1. Deduplicate Exact Duplicate Rows
        exact_seen = set()
        deduped = []
        for r in all_rows:
            order_id = str(r.get("ORDER_ID", "")).strip()
            sig = (
                order_id,
                r.get("CUSTOMER_ID"),
                r.get("PRODUCT_ID"),
                r.get("QUANTITY"),
                r.get("ORDER_DATE"),
                r.get("DELIVERY_DATE"),
                r.get("ORDER_STATUS"),
                r.get("LAST_UPDATED_TS")
            )
            if sig in exact_seen:
                self.qm.log_issue(
                    file_name=r.get("_SOURCE_FILE"),
                    record_key=order_id,
                    rule_name="EXACT_DUPLICATE_ROW",
                    severity="TRANSFORM",
                    action_taken="DEDUP",
                    error_message=f"Deduplicated identical transaction row for order {order_id}",
                    raw_payload=r
                )
            else:
                exact_seen.add(sig)
                deduped.append(r)

        # Group by ORDER_ID
        orders_by_id = defaultdict(list)
        for r in deduped:
            oid = str(r.get("ORDER_ID", "")).strip()
            orders_by_id[oid].append(r)

        resolved_orders = []

        for oid, group in orders_by_id.items():
            if len(group) == 1:
                resolved_orders.append(group[0])
                continue

            # Multiple records for same ORDER_ID
            # Check for conflicting duplicates with same timestamp
            ts_groups = defaultdict(list)
            for r in group:
                ts = str(r.get("LAST_UPDATED_TS", "")).strip()
                ts_groups[ts].append(r)

            has_conflict = False
            for ts, ts_records in ts_groups.items():
                if len(ts_records) > 1:
                    has_conflict = True
                    self.qm.log_issue(
                        file_name=group[0].get("_SOURCE_FILE"),
                        record_key=oid,
                        rule_name="CONFLICTING_DUPLICATE_SAME_TS",
                        severity="QUARANTINE",
                        action_taken="QUARANTINE - cannot decide winner; document assumption",
                        error_message=f"Order {oid} has conflicting versions at identical timestamp {ts}",
                        raw_payload=group[0]
                    )
                    break

            if has_conflict:
                continue  # Quarantined, do not load to fact

            # Sort by LAST_UPDATED_TS descending to pick winner
            group.sort(key=lambda r: str(r.get("LAST_UPDATED_TS", "")), reverse=True)
            winner = group[0]
            second = group[1]

            # Determine whether this was Cross-File or Same-File CDC update
            is_cross_file = (winner.get("_SOURCE_FILE") != second.get("_SOURCE_FILE"))
            
            rule_name = "CROSS_FILE_CDC_UPDATE" if is_cross_file else "CDC_STATUS_UPDATE_SAME_ID"
            action = "UPSERT over clean-file version (newer LAST_UPDATED_TS)" if is_cross_file else "KEEP LATEST by LAST_UPDATED_TS (CDC upsert)"
            
            self.qm.log_issue(
                file_name=winner.get("_SOURCE_FILE"),
                record_key=oid,
                rule_name=rule_name,
                severity="TRANSFORM",
                action_taken=action,
                error_message=f"CDC Upsert: Picked version from {winner.get('_SOURCE_FILE')} updated at {winner.get('LAST_UPDATED_TS')}",
                raw_payload=winner
            )

            resolved_orders.append(winner)

        return resolved_orders
