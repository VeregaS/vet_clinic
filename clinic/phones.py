import re

from django.core.exceptions import ValidationError


def normalize_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", phone)
    if not re.fullmatch(r"[78][0-9]{10}", digits):
        raise ValidationError("Введите 11 цифр номера, начиная с 7 или 8.")
    return "+7" + digits[1:]
