"""
Data Quality Standardization and Cleaning Engine
Implements canonical transformations for Couriers, Statuses, Cities, Dates, and Product IDs
"""

import re
from datetime import datetime
from src.config import (
    STATUS_NORMALIZATION_MAP,
    COURIER_CANONICAL_MAP,
    CITY_ALIAS_MAP,
    SEGMENT_NORMALIZATION_MAP,
)

DATE_FORMATS = [
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%d-%m-%Y",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%m-%d-%Y",
    "%d-%b-%Y",  # e.g. 12-Jan-2026
    "%d/%b/%Y",
    "%Y-%b-%d",
]

def clean_string(val: str) -> str:
    """Trim leading/trailing whitespace."""
    if val is None:
        return ""
    return str(val).strip()

def parse_date_robust(date_str: str):
    """
    Attempts to parse date using multiple known formats.
    Returns (standardized_iso_date_str, is_valid, is_mixed_format).
    If plain text or invalid calendar date, returns (None, False, False).
    """
    if not date_str or not str(date_str).strip():
        return None, True, False  # Empty/null date may be valid for Cancelled/In-Transit
    
    val = str(date_str).strip()
    
    # Catch plain text or zero dates immediately
    if val in {"0000-00-00", "00-00-0000", "null", "none", "cancelled", "unknown"}:
        return None, False, False
    
    if re.search(r"[a-zA-Z]{4,}", val):  # Words longer than 3 chars (like 'Delivered', 'Cancelled')
        return None, False, False

    # Check for invalid calendar dates like 2026/13/40 or 2026-02-30
    for fmt in DATE_FORMATS:
        try:
            parsed = datetime.strptime(val, fmt)
            iso_str = parsed.strftime("%Y-%m-%d")
            # If input was not already strictly YYYY-MM-DD, mark as mixed format
            is_mixed = (fmt != "%Y-%m-%d")
            return iso_str, True, is_mixed
        except (ValueError, TypeError):
            continue
            
    return None, False, False

def normalize_status(status_str: str):
    """Normalizes order status to canonical values: Delivered, In-Transit, Cancelled, Returned."""
    if not status_str:
        return None, False
    cleaned = status_str.strip().lower()
    canonical = STATUS_NORMALIZATION_MAP.get(cleaned)
    if canonical:
        is_variant = (status_str != canonical)
        return canonical, is_variant
    return status_str.strip().title(), False

def normalize_courier(courier_str: str):
    """Standardizes courier name and detects variants."""
    if not courier_str:
        return "", False
    cleaned = courier_str.strip()
    lookup = cleaned.lower()
    
    canonical = COURIER_CANONICAL_MAP.get(lookup)
    if canonical:
        is_variant = (courier_str != canonical)
        return canonical, is_variant
        
    return cleaned, False

def normalize_city(city_str: str):
    """Trims whitespace, title-cases city, and resolves city aliases."""
    if not city_str or not str(city_str).strip():
        return "UNKNOWN", False, False
        
    cleaned = str(city_str).strip().title()
    lookup = cleaned.lower()
    
    is_alias = False
    if lookup in CITY_ALIAS_MAP:
        cleaned = CITY_ALIAS_MAP[lookup]
        is_alias = True
        
    is_case_variant = (city_str != cleaned and not is_alias)
    return cleaned, is_case_variant, is_alias

def normalize_segment(segment_str: str):
    """Standardizes customer segment casing."""
    if not segment_str:
        return "Regular", False
    cleaned = segment_str.strip().lower()
    canonical = SEGMENT_NORMALIZATION_MAP.get(cleaned, "Regular")
    is_variant = (segment_str != canonical)
    return canonical, is_variant

def normalize_product_id(product_id_str: str):
    """Upper-cases and trims product ID."""
    if not product_id_str:
        return "", False, False
    trimmed = product_id_str.strip()
    upper = trimmed.upper()
    had_trailing = (len(product_id_str) != len(trimmed))
    was_lowercase = (trimmed != upper)
    return upper, had_trailing, was_lowercase

def is_valid_email(email_str: str) -> bool:
    """Validates email format."""
    if not email_str:
        return True  # null email handled separately
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return bool(re.match(pattern, email_str.strip()))
