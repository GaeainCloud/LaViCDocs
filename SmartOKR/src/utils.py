"""SmartOKR utility functions."""

import uuid
from datetime import datetime, date


def generate_id(prefix: str) -> str:
    """Generate a unique ID like 'obj-20250207-a1b2c3'."""
    date_str = datetime.now().strftime("%Y%m%d")
    short_uuid = uuid.uuid4().hex[:6]
    return f"{prefix}-{date_str}-{short_uuid}"


def parse_period(period: str) -> tuple:
    """Convert period string to (start_date, end_date).

    Supports:
      - '2025-Q1' -> (2025-01-01, 2025-03-31)
      - '2025-01' -> (2025-01-01, 2025-01-31)
    """
    if "Q" in period.upper():
        year, q = period.upper().split("-Q")
        year = int(year)
        quarter = int(q)
        start_month = (quarter - 1) * 3 + 1
        end_month = start_month + 2
        start = date(year, start_month, 1)
        if end_month == 12:
            end = date(year, 12, 31)
        else:
            end = date(year, end_month + 1, 1).replace(day=1)
            from datetime import timedelta
            end = end - timedelta(days=1)
        return start.isoformat(), end.isoformat()
    elif len(period) == 7:  # YYYY-MM
        year, month = period.split("-")
        year, month = int(year), int(month)
        start = date(year, month, 1)
        if month == 12:
            end = date(year, 12, 31)
        else:
            from datetime import timedelta
            end = date(year, month + 1, 1) - timedelta(days=1)
        return start.isoformat(), end.isoformat()
    return None, None


def now_iso() -> str:
    """Return current timestamp in ISO 8601."""
    return datetime.now().isoformat() + "Z"


# BSC dimension definitions with Chinese labels
BSC_DIMENSIONS = {
    "financial": {"label": "财务", "label_en": "Financial"},
    "customer": {"label": "客户", "label_en": "Customer"},
    "internal_process": {"label": "内部流程", "label_en": "Internal Process"},
    "learning_growth": {"label": "学习与成长", "label_en": "Learning & Growth"},
}

# Role-based default BSC weights
ROLE_WEIGHT_PRESETS = {
    "engineer": {
        "financial": 0.10,
        "customer": 0.20,
        "internal_process": 0.45,
        "learning_growth": 0.25,
    },
    "product_manager": {
        "financial": 0.20,
        "customer": 0.35,
        "internal_process": 0.25,
        "learning_growth": 0.20,
    },
    "sales": {
        "financial": 0.40,
        "customer": 0.30,
        "internal_process": 0.15,
        "learning_growth": 0.15,
    },
    "designer": {
        "financial": 0.10,
        "customer": 0.35,
        "internal_process": 0.30,
        "learning_growth": 0.25,
    },
    "manager": {
        "financial": 0.25,
        "customer": 0.25,
        "internal_process": 0.30,
        "learning_growth": 0.20,
    },
    "researcher": {
        "financial": 0.10,
        "customer": 0.15,
        "internal_process": 0.35,
        "learning_growth": 0.40,
    },
    "operations": {
        "financial": 0.25,
        "customer": 0.25,
        "internal_process": 0.35,
        "learning_growth": 0.15,
    },
    "default": {
        "financial": 0.20,
        "customer": 0.25,
        "internal_process": 0.35,
        "learning_growth": 0.20,
    },
}
