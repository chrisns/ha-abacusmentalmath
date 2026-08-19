"""Constants for the Abacus Mental Math integration."""
from __future__ import annotations

from datetime import timedelta

DOMAIN = "abacusmentalmath"

API_BASE_URL = "https://api.abacusmentalmath.com"
MANUFACTURER = "Abacus Mental Math"

DEFAULT_SCAN_INTERVAL = timedelta(minutes=15)
MIN_SCAN_INTERVAL = timedelta(minutes=5)
MAX_SCAN_INTERVAL = timedelta(hours=6)

CONF_SCAN_INTERVAL_MINUTES = "scan_interval_minutes"
