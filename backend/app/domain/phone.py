import re

_DIGITS = re.compile(r"\d+")


# Normalizes Ukrainian numbers to E.164: "067 123-45-67", "380671234567" and
# "+380671234567" all become "+380671234567". Raises ValueError otherwise.
def normalize_phone(raw: str) -> str:
    digits = "".join(_DIGITS.findall(raw))
    if len(digits) == 10 and digits.startswith("0"):
        digits = "38" + digits
    if len(digits) == 12 and digits.startswith("380"):
        return "+" + digits
    raise ValueError("Номер телефону має бути у форматі +380XXXXXXXXX")
