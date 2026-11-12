import re
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,50}$")
def is_valid_email(value: str) -> bool:
    return bool(value and EMAIL_RE.match(value.strip()))


def is_valid_username(value: str) -> bool:
    return bool(value and USERNAME_RE.match(value.strip()))


def phone_digits(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    if len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    return digits


def normalize_phone(value: str):
    digits = phone_digits(value)
    return digits or None


def is_valid_phone(value: str, required: bool = False) -> bool:
    digits = phone_digits(value)
    if not digits:
        return not required
    return len(digits) == 10 and digits.isdigit()


def is_strong_password(value: str) -> bool:
    if not value or len(value) < 8:
        return False
    has_letter = any(ch.isalpha() for ch in value)
    has_digit = any(ch.isdigit() for ch in value)
    return has_letter and has_digit


def parse_date(value: str):
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return False


def parse_time(value: str):
    if not value:
        return None
    try:
        return time.fromisoformat(value)
    except ValueError:
        try:
            return datetime.strptime(value, "%H:%M").time()
        except ValueError:
            return False


def is_valid_measurement(value, maximum: Decimal = Decimal("999.99")) -> bool:
    if value is None:
        return True
    try:
        number = Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        return False
    return number >= 0 and number <= maximum and number.as_tuple().exponent >= -2
