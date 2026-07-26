"""Constants for the HET.uz integration."""

from datetime import timedelta

DOMAIN = "het_uz"

API_BASE_URL = "https://cabinet-api.het.uz/household-consumer/v1/mobile-cabinet"

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_3) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/44.0.2403.89 Safari/537.36"
)

CONF_LOGIN = "login"
CONF_PASSWORD = "password"

DEFAULT_SCAN_INTERVAL = timedelta(minutes=30)

STORAGE_AUTH = "auth"
