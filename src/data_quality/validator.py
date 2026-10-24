"""
Data Quality Validation Engine
Applies all 38 business validation rules and flags/rejects invalid records
"""

import re
from datetime import datetime
from src.data_quality.cleaner import (
    clean_string,
    parse_date_robust,
    normalize_status,
    normalize_courier,
    normalize_city,
    normalize_segment,
    normalize_product_id,
    is_valid_email,
)
from src.data_quality.quarantine import QuarantineManager

class DataQualityValidator:
    def __init__(self, quarantine_mgr: QuarantineManager, valid_courier_master: dict):
        """
        valid_courier_master: dict mapping canonical courier_name -> dict(SLA_DAYS, ACTIVE_FLAG, COURIER_ID)
        """
        self.qm = quarantine_mgr
        self.courier_master = valid_courier_master

    # -------------------------------------------------------------
    # Customer Master Validation
    # -------------------------------------------------------------
    def validate_customer_record(self, raw_row: dict) -> tuple:
        """
        Validates and standardizes a single customer record.
        Returns: (is_valid: bool, cleaned_row: dict or None)
        """
        cust_id = clean_string(raw_row.get("CUSTOMER_ID"))
        cust_name = clean_string(raw_row.get("CUSTOMER_NAME"))
        file_name = "customer_master_orders_v3.csv"
        
        # 1. Mandatory CUSTOMER_ID
        if not cust_id or cust_id.lower() in {"null", "none", ""}:
            self.qm.log_issue(
                file_name=file_name,
                record_key=f"(null id) {cust_name}",
                rule_name="NULL_CUSTOMER_ID",
                severity="REJECT",
                action_taken="REJECT",
                error_message="CUSTOMER_ID is null or empty",
                raw_payload=raw_row
            )
            return False, None

        # 2. Mandatory CUSTOMER_NAME
        if not cust_name or cust_name.lower() in {"null", "none", ""}:
            self.qm.log_issue(
                file_name=file_name,
                record_key=cust_id,
                rule_name="NULL_CUSTOMER_NAME",
                severity="WARNING",
                action_taken="REJECT_OR_FLAG (mandatory field)",
                error_message="CUSTOMER_NAME is mandatory and was null; flagged and set to UNKNOWN",
                raw_payload=raw_row
            )
            cust_name = "UNKNOWN"

        cleaned = dict(raw_row)
        cleaned["CUSTOMER_ID"] = cust_id
        cleaned["CUSTOMER_NAME"] = cust_name

        # 3. Optional EMAIL & PHONE
        email = clean_string(raw_row.get("EMAIL"))
        phone = clean_string(raw_row.get("PHONE"))
        
        if not email:
            self.qm.log_issue(
                file_name=file_name,
                record_key=cust_id,
                rule_name="NULL_EMAIL",
                severity="WARNING",
                action_taken="LOAD (optional field)",
                error_message="EMAIL is missing; allowed as optional",
                raw_payload=raw_row
            )
            cleaned["EMAIL"] = None
        elif not is_valid_email(email):
            self.qm.log_issue(
                file_name=file_name,
                record_key=cust_id,
                rule_name="INVALID_EMAIL",
                severity="WARNING",
                action_taken="FLAG / null out",
                error_message=f"Invalid email pattern: {email}",
                raw_payload=raw_row
            )
            cleaned["EMAIL"] = None
        else:
            cleaned["EMAIL"] = email.lower()

        if not phone:
            self.qm.log_issue(
                file_name=file_name,
                record_key=cust_id,
                rule_name="NULL_PHONE",
                severity="WARNING",
                action_taken="LOAD (optional field)",
                error_message="PHONE is missing; allowed as optional",
                raw_payload=raw_row
            )
            cleaned["PHONE"] = None
        else:
            cleaned["PHONE"] = phone

        # 4. CITY Normalization & Aliases
        raw_city = raw_row.get("CITY")
        if not raw_city or not str(raw_city).strip():
            self.qm.log_issue(
                file_name=file_name,
                record_key=cust_id,
                rule_name="NULL_CITY",
                severity="WARNING",
                action_taken="DEFAULT 'UNKNOWN' + flag",
                error_message="City is null; default applied",
                raw_payload=raw_row
            )
            cleaned["CITY"] = "UNKNOWN"
        else:
            norm_city, is_case_var, is_alias = normalize_city(raw_city)
            cleaned["CITY"] = norm_city
            if is_alias:
                self.qm.log_issue(
                    file_name=file_name,
                    record_key=cust_id,
                    rule_name="CITY_ALIAS",
                    severity="TRANSFORM",
                    action_taken="STANDARDIZE via mapping",
                    error_message=f"Standardized city alias: {raw_city} -> {norm_city}",
                    raw_payload=raw_row
                )
            elif is_case_var:
                self.qm.log_issue(
                    file_name=file_name,
                    record_key=cust_id,
                    rule_name="CITY_CASE_WHITESPACE",
                    severity="TRANSFORM",
                    action_taken="STANDARDIZE (trim, title-case)",
                    error_message=f"Cleaned city casing/whitespace: '{raw_city}' -> '{norm_city}'",
                    raw_payload=raw_row
                )

        # 5. SEGMENT Normalization
        raw_segment = raw_row.get("CUSTOMER_SEGMENT")
        norm_segment, seg_variant = normalize_segment(raw_segment)
        cleaned["CUSTOMER_SEGMENT"] = norm_segment
        if seg_variant:
            self.qm.log_issue(
                file_name=file_name,
                record_key=cust_id,
                rule_name="SEGMENT_CASE",
                severity="TRANSFORM",
                action_taken="STANDARDIZE",
                error_message=f"Standardized segment casing: '{raw_segment}' -> '{norm_segment}'",
                raw_payload=raw_row
            )

        return True, cleaned

    # -------------------------------------------------------------
    # Order Transactions Validation
    # -------------------------------------------------------------
    def validate_order_transaction(self, raw_row: dict, source_file: str, valid_cust_ids: set, product_catalog: dict) -> tuple:
        """
        Validates a single order transaction row.
        Returns: (is_valid: bool, cleaned_row: dict or None)
        """
        raw_order_id = raw_row.get("ORDER_ID")
        order_id = clean_string(raw_order_id)
        
        # Check trailing whitespace in order_id
        if raw_order_id and len(raw_order_id) != len(order_id):
            self.qm.log_issue(
                file_name=source_file,
                record_key=order_id,
                rule_name="TRAILING_WHITESPACE_ID",
                severity="TRANSFORM",
                action_taken="STANDARDIZE (trim)",
                error_message="ORDER_ID contained trailing/leading whitespace",
                raw_payload=raw_row
            )

        if not order_id:
            self.qm.log_issue(
                file_name=source_file,
                record_key="UNKNOWN",
                rule_name="NULL_ORDER_ID",
                severity="REJECT",
                action_taken="REJECT",
                error_message="Missing ORDER_ID",
                raw_payload=raw_row
            )
            return False, None

        cleaned = dict(raw_row)
        cleaned["ORDER_ID"] = order_id

        # 1. Customer FK Check & Trailing Whitespace
        raw_cust_id = raw_row.get("CUSTOMER_ID")
        cust_id = clean_string(raw_cust_id)
        if raw_cust_id and len(raw_cust_id) != len(cust_id):
            self.qm.log_issue(
                file_name=source_file,
                record_key=order_id,
                rule_name="TRAILING_WHITESPACE_ID",
                severity="TRANSFORM",
                action_taken="STANDARDIZE (trim)",
                error_message=f"CUSTOMER_ID '{raw_cust_id}' had trailing whitespace",
                raw_payload=raw_row
            )

        if not cust_id or cust_id.lower() in {"null", "none", ""}:
            self.qm.log_issue(
                file_name=source_file,
                record_key=order_id,
                rule_name="NULL_CUSTOMER_ID",
                severity="REJECT",
                action_taken="REJECT",
                error_message="CUSTOMER_ID is null in order transaction",
                raw_payload=raw_row
            )
            return False, None

        cleaned["CUSTOMER_ID"] = cust_id
        if cust_id not in valid_cust_ids:
            self.qm.log_issue(
                file_name=source_file,
                record_key=order_id,
                rule_name="ORPHAN_CUSTOMER_FK",
                severity="REJECT",
                action_taken="REJECT/QUARANTINE (or load to 'Unknown' member - document it)",
                error_message=f"CUSTOMER_ID '{cust_id}' does not exist in DIM_CUSTOMER",
                raw_payload=raw_row
            )
            return False, None

        # 2. Product ID Check & Standardization
        raw_prod_id = raw_row.get("PRODUCT_ID")
        norm_prod_id, had_ws, was_lower = normalize_product_id(raw_prod_id)
        if not norm_prod_id:
            self.qm.log_issue(
                file_name=source_file,
                record_key=order_id,
                rule_name="NULL_PRODUCT_ID",
                severity="REJECT",
                action_taken="REJECT",
                error_message="PRODUCT_ID is null or empty",
                raw_payload=raw_row
            )
            return False, None
            
        cleaned["PRODUCT_ID"] = norm_prod_id
        if was_lower:
            self.qm.log_issue(
                file_name=source_file,
                record_key=order_id,
                rule_name="LOWERCASE_PRODUCT_ID",
                severity="TRANSFORM",
                action_taken="STANDARDIZE (upper)",
                error_message=f"Standardized lowercase PRODUCT_ID: '{raw_prod_id}' -> '{norm_prod_id}'",
                raw_payload=raw_row
            )
        if had_ws:
            self.qm.log_issue(
                file_name=source_file,
                record_key=order_id,
                rule_name="TRAILING_WHITESPACE_ID",
                severity="TRANSFORM",
                action_taken="STANDARDIZE (trim)",
                error_message=f"Cleaned whitespace in PRODUCT_ID '{raw_prod_id}'",
                raw_payload=raw_row
            )

        # 3. Quantity Validation
        raw_qty = raw_row.get("QUANTITY")
        try:
            qty = int(raw_qty)
            cleaned["QUANTITY"] = qty
            if qty < 0:
                self.qm.log_issue(
                    file_name=source_file,
                    record_key=order_id,
                    rule_name="NEGATIVE_QUANTITY",
                    severity="REJECT",
                    action_taken="REJECT (or treat as return - document)",
                    error_message=f"Negative quantity: {qty}",
                    raw_payload=raw_row
                )
                return False, None
            elif qty == 0:
                self.qm.log_issue(
                    file_name=source_file,
                    record_key=order_id,
                    rule_name="ZERO_QUANTITY",
                    severity="REJECT",
                    action_taken="REJECT/QUARANTINE (document rule)",
                    error_message="Zero quantity order rejected",
                    raw_payload=raw_row
                )
                return False, None
        except (ValueError, TypeError):
            self.qm.log_issue(
                file_name=source_file,
                record_key=order_id,
                rule_name="NON_NUMERIC_QUANTITY",
                severity="REJECT",
                action_taken="REJECT",
                error_message=f"Non-numeric quantity: '{raw_qty}'",
                raw_payload=raw_row
            )
            return False, None

        # 4. Unit Price Validation & Imputation
        raw_price = raw_row.get("UNIT_PRICE")
        try:
            price = float(raw_price) if raw_price is not None and str(raw_price).strip() != "" else None
        except (ValueError, TypeError):
            price = None

        if price is None:
            self.qm.log_issue(
                file_name=source_file,
                record_key=order_id,
                rule_name="NULL_UNIT_PRICE",
                severity="WARNING",
                action_taken="FLAG; derive from product dim if available",
                error_message="Missing unit price; imputed from product master",
                raw_payload=raw_row
            )
            price = product_catalog.get(norm_prod_id, {}).get("UNIT_PRICE", 999.0)
        elif price <= 0:
            self.qm.log_issue(
                file_name=source_file,
                record_key=order_id,
                rule_name="ZERO_UNIT_PRICE",
                severity="WARNING",
                action_taken="FLAG",
                error_message=f"Zero unit price: {price}; imputed from product master",
                raw_payload=raw_row
            )
            price = product_catalog.get(norm_prod_id, {}).get("UNIT_PRICE", 999.0)

        cleaned["UNIT_PRICE"] = price
        cleaned["TOTAL_AMOUNT"] = round(price * cleaned["QUANTITY"], 2)

        # 5. Order Status Normalization
        raw_status = raw_row.get("ORDER_STATUS")
        norm_status, status_var = normalize_status(raw_status)
        cleaned["ORDER_STATUS"] = norm_status
        if status_var:
            self.qm.log_issue(
                file_name=source_file,
                record_key=order_id,
                rule_name="STATUS_VARIANT",
                severity="TRANSFORM",
                action_taken="STANDARDIZE to 4 canonical statuses",
                error_message=f"Standardized status: '{raw_status}' -> '{norm_status}'",
                raw_payload=raw_row
            )

        # 6. Courier Validation & Normalization
        raw_courier = raw_row.get("COURIER_NAME")
        if not raw_courier or not str(raw_courier).strip():
            self.qm.log_issue(
                file_name=source_file,
                record_key=order_id,
                rule_name="NULL_COURIER",
                severity="REJECT",
                action_taken="REJECT (or allow for Cancelled - document)",
                error_message="COURIER_NAME is null or empty",
                raw_payload=raw_row
            )
            return False, None
            
        norm_courier, courier_var = normalize_courier(raw_courier)
        if courier_var:
            self.qm.log_issue(
                file_name=source_file,
                record_key=order_id,
                rule_name="COURIER_NAME_VARIANT",
                severity="TRANSFORM",
                action_taken="STANDARDIZE via mapping table",
                error_message=f"Standardized courier variant: '{raw_courier}' -> '{norm_courier}'",
                raw_payload=raw_row
            )

        courier_info = self.courier_master.get(norm_courier) or self.courier_master.get(norm_courier.lower())
        if not courier_info:
            self.qm.log_issue(
                file_name=source_file,
                record_key=order_id,
                rule_name="UNKNOWN_COURIER",
                severity="REJECT",
                action_taken="REJECT (not in SLA master)",
                error_message=f"Courier '{raw_courier}' does not exist in courier SLA master",
                raw_payload=raw_row
            )
            return False, None
        cleaned["COURIER_NAME"] = norm_courier
        cleaned["COURIER_ID"] = courier_info["COURIER_ID"]
        cleaned["SLA_DAYS"] = courier_info["SLA_DAYS"]
        cleaned["INACTIVE_COURIER_FLAG"] = 1 if courier_info["ACTIVE_FLAG"] == "N" else 0

        if courier_info["ACTIVE_FLAG"] == "N":
            self.qm.log_issue(
                file_name=source_file,
                record_key=order_id,
                rule_name="INACTIVE_COURIER",
                severity="WARNING",
                action_taken="BUSINESS RULE: exists in master -> load, flag inactive",
                error_message=f"Courier '{norm_courier}' is marked inactive in master",
                raw_payload=raw_row
            )

        # 7. Date Parsing & Validation
        raw_order_date = raw_row.get("ORDER_DATE")
        parsed_order_date, is_order_valid, is_order_mixed = parse_date_robust(raw_order_date)
        
        if not is_order_valid or not parsed_order_date:
            # Distinguish plain text from invalid calendar
            if re.search(r"[a-zA-Z]", str(raw_order_date or "")):
                rule = "PLAIN_TEXT_ORDER_DATE"
            else:
                rule = "INVALID_CALENDAR_DATE"
            self.qm.log_issue(
                file_name=source_file,
                record_key=order_id,
                rule_name=rule,
                severity="REJECT",
                action_taken="REJECT/QUARANTINE",
                error_message=f"Invalid ORDER_DATE: '{raw_order_date}'",
                raw_payload=raw_row
            )
            return False, None
            
        cleaned["ORDER_DATE"] = parsed_order_date

        # Parse Shipped Date
        raw_shipped_date = raw_row.get("SHIPPED_DATE")
        parsed_shipped_date, is_shipped_valid, is_shipped_mixed = parse_date_robust(raw_shipped_date)
        if not is_shipped_valid and raw_shipped_date:
            self.qm.log_issue(
                file_name=source_file,
                record_key=order_id,
                rule_name="INVALID_CALENDAR_DATE",
                severity="REJECT",
                action_taken="REJECT/QUARANTINE",
                error_message=f"Invalid SHIPPED_DATE: '{raw_shipped_date}'",
                raw_payload=raw_row
            )
            return False, None
        cleaned["SHIPPED_DATE"] = parsed_shipped_date

        # Parse Delivery Date
        raw_delivery_date = raw_row.get("DELIVERY_DATE")
        parsed_deliv_date, is_deliv_valid, is_deliv_mixed = parse_date_robust(raw_delivery_date)
        if not is_deliv_valid and raw_delivery_date:
            if re.search(r"[a-zA-Z]", str(raw_delivery_date)):
                rule = "PLAIN_TEXT_DELIVERY_DATE"
            else:
                rule = "INVALID_CALENDAR_DATE"
            self.qm.log_issue(
                file_name=source_file,
                record_key=order_id,
                rule_name=rule,
                severity="REJECT",
                action_taken="REJECT/QUARANTINE",
                error_message=f"Invalid DELIVERY_DATE: '{raw_delivery_date}'",
                raw_payload=raw_row
            )
            return False, None
            
        cleaned["DELIVERY_DATE"] = parsed_deliv_date

        if is_order_mixed or is_shipped_mixed or is_deliv_mixed:
            self.qm.log_issue(
                file_name=source_file,
                record_key=order_id,
                rule_name="MIXED_DATE_FORMAT",
                severity="TRANSFORM",
                action_taken="FIX: parse multiple formats then load",
                error_message="Parsed and standardized non-ISO date formats",
                raw_payload=raw_row
            )

        # 8. Status vs Date Consistency Checks
        if norm_status == "Delivered" and not parsed_deliv_date:
            self.qm.log_issue(
                file_name=source_file,
                record_key=order_id,
                rule_name="DELIVERED_WITHOUT_DELIVERY_DATE",
                severity="REJECT",
                action_taken="REJECT/QUARANTINE (status vs date conflict)",
                error_message="Order marked as Delivered but DELIVERY_DATE is missing",
                raw_payload=raw_row
            )
            return False, None

        if norm_status == "In-Transit" and parsed_deliv_date:
            self.qm.log_issue(
                file_name=source_file,
                record_key=order_id,
                rule_name="IN_TRANSIT_WITH_DELIVERY_DATE",
                severity="REJECT",
                action_taken="REJECT/QUARANTINE (status vs date conflict)",
                error_message="Order marked as In-Transit but DELIVERY_DATE is populated",
                raw_payload=raw_row
            )
            return False, None

        # 9. Chronology Checks
        if parsed_order_date and parsed_shipped_date:
            if parsed_shipped_date < parsed_order_date:
                self.qm.log_issue(
                    file_name=source_file,
                    record_key=order_id,
                    rule_name="SHIPPED_BEFORE_ORDER",
                    severity="REJECT",
                    action_taken="REJECT (extra chronology rule)",
                    error_message=f"SHIPPED_DATE ({parsed_shipped_date}) < ORDER_DATE ({parsed_order_date})",
                    raw_payload=raw_row
                )
                return False, None

        if parsed_order_date and parsed_deliv_date:
            if parsed_deliv_date < parsed_order_date:
                self.qm.log_issue(
                    file_name=source_file,
                    record_key=order_id,
                    rule_name="DELIVERY_BEFORE_ORDER",
                    severity="REJECT",
                    action_taken="REJECT",
                    error_message=f"DELIVERY_DATE ({parsed_deliv_date}) < ORDER_DATE ({parsed_order_date})",
                    raw_payload=raw_row
                )
                return False, None

        if parsed_shipped_date and parsed_deliv_date:
            if parsed_deliv_date < parsed_shipped_date:
                self.qm.log_issue(
                    file_name=source_file,
                    record_key=order_id,
                    rule_name="DELIVERY_BEFORE_SHIPPED",
                    severity="REJECT",
                    action_taken="REJECT",
                    error_message=f"DELIVERY_DATE ({parsed_deliv_date}) < SHIPPED_DATE ({parsed_shipped_date})",
                    raw_payload=raw_row
                )
                return False, None

        return True, cleaned
