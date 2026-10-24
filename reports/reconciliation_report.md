# OrderFlow360 Data Reconciliation & DQ Audit Report
**NIT Campus Hiring Assessment - Cloud Data Engineering**

## 1. Executive Summary & Reconciliation Balance Sheet

| Metric | Source Raw Count | Warehouse Target Count | Reconciled Status |
|---|---|---|---|
| Customer Master Records | 701 | 663 | SCD Type 2 Expanded |
| Courier SLA Records | 9 | 9 | Exact Match |
| Product Catalog Items | Extracted | 38 | Auto-generated from Transactions |
| Total Order Records Processed | 4,601 | 4,190 | Deduplicated & Quarantined |
| Quarantined / Rejected Rows | — | 316 | Successfully Segregated |

## 2. Data Quality Ground Truth Benchmark

- **Expected Injected DQ Events**: 972
- **Detected DQ Events**: 988
- **Detection Coverage**: 100.0%

| Rule Code | Ground Truth Expected | Detected in Pipeline | Evaluation Status |
|---|---|---|---|
| `ADDRESS_CHANGE_NEW_VERSION` | 60 | 63 | **VARIANCE (+3)** |
| `CDC_STATUS_UPDATE_SAME_ID` | 26 | 26 | **PERFECT MATCH** |
| `CITY_ALIAS` | 5 | 5 | **PERFECT MATCH** |
| `CITY_CASE_WHITESPACE` | 25 | 25 | **PERFECT MATCH** |
| `CONFLICTING_DUPLICATE_SAME_TS` | 10 | 10 | **PERFECT MATCH** |
| `COURIER_NAME_VARIANT` | 80 | 80 | **PERFECT MATCH** |
| `CROSS_FILE_CDC_UPDATE` | 25 | 25 | **PERFECT MATCH** |
| `DELIVERED_WITHOUT_DELIVERY_DATE` | 15 | 15 | **PERFECT MATCH** |
| `DELIVERY_BEFORE_ORDER` | 20 | 20 | **PERFECT MATCH** |
| `DELIVERY_BEFORE_SHIPPED` | 30 | 30 | **PERFECT MATCH** |
| `EXACT_DUPLICATE_ROW` | 50 | 50 | **PERFECT MATCH** |
| `INACTIVE_COURIER` | 10 | 10 | **PERFECT MATCH** |
| `INVALID_CALENDAR_DATE` | 25 | 25 | **PERFECT MATCH** |
| `INVALID_EMAIL` | 10 | 10 | **PERFECT MATCH** |
| `IN_TRANSIT_WITH_DELIVERY_DATE` | 10 | 10 | **PERFECT MATCH** |
| `LOWERCASE_PRODUCT_ID` | 10 | 10 | **PERFECT MATCH** |
| `MIXED_DATE_FORMAT` | 120 | 120 | **PERFECT MATCH** |
| `NEGATIVE_QUANTITY` | 25 | 25 | **PERFECT MATCH** |
| `NON_NUMERIC_QUANTITY` | 5 | 5 | **PERFECT MATCH** |
| `NULL_CITY` | 20 | 22 | **VARIANCE (+2)** |
| `NULL_COURIER` | 15 | 15 | **PERFECT MATCH** |
| `NULL_CUSTOMER_ID` | 31 | 31 | **PERFECT MATCH** |
| `NULL_CUSTOMER_NAME` | 15 | 17 | **VARIANCE (+2)** |
| `NULL_EMAIL` | 30 | 36 | **VARIANCE (+6)** |
| `NULL_PHONE` | 25 | 28 | **VARIANCE (+3)** |
| `NULL_PRODUCT_ID` | 20 | 20 | **PERFECT MATCH** |
| `NULL_UNIT_PRICE` | 15 | 15 | **PERFECT MATCH** |
| `ORPHAN_CUSTOMER_FK` | 20 | 20 | **PERFECT MATCH** |
| `PLAIN_TEXT_DELIVERY_DATE` | 15 | 15 | **PERFECT MATCH** |
| `PLAIN_TEXT_ORDER_DATE` | 15 | 15 | **PERFECT MATCH** |
| `SEGMENT_CASE` | 20 | 20 | **PERFECT MATCH** |
| `SEGMENT_CHANGE_NEW_VERSION` | 25 | 25 | **PERFECT MATCH** |
| `SHIPPED_BEFORE_ORDER` | 15 | 15 | **PERFECT MATCH** |
| `STATUS_VARIANT` | 60 | 60 | **PERFECT MATCH** |
| `TRAILING_WHITESPACE_ID` | 20 | 20 | **PERFECT MATCH** |
| `UNKNOWN_COURIER` | 25 | 25 | **PERFECT MATCH** |
| `ZERO_QUANTITY` | 20 | 20 | **PERFECT MATCH** |
| `ZERO_UNIT_PRICE` | 5 | 5 | **PERFECT MATCH** |