from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from clinic.phones import normalize_phone


class PhoneNormalizationTests(SimpleTestCase):
    def test_equivalent_and_already_normalized_numbers(self):
        for phone in ("8 (999) 000-00-00", "+7 999 000 00 00", "+79990000000"):
            with self.subTest(phone=phone):
                self.assertEqual(normalize_phone(phone), "+79990000000")

    def test_rejects_wrong_length_or_prefix(self):
        for phone in ("", "8999000000", "+799900000000", "+19990000000"):
            with self.subTest(phone=phone), self.assertRaises(ValidationError):
                normalize_phone(phone)
