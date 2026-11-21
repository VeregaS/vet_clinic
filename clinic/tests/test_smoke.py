from datetime import date, datetime, timedelta
from datetime import timezone as dt_timezone
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from clinic.constants import TIME_CHOICES
from clinic.models import Appointment, Doctor, Patient


class DemoTests(TestCase):
    def setUp(self):
        self.instant = datetime(2030, 5, 1, 21, 10, tzinfo=dt_timezone.utc)
        self.enterContext(timezone.override("Europe/Moscow"))
        self.enterContext(patch("django.utils.timezone.now", return_value=self.instant))

    def test_home_displays_booking_form(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        for field in ("doctor", "date", "time_slot", "owner_phone"):
            self.assertIn(field, response.context["form"].fields)

    def test_initial_data_links_appointments(self):
        call_command("seed_demo", stdout=StringIO())
        visits = list(Appointment.objects.select_related("doctor", "patient"))
        self.assertTrue(visits)
        for visit in visits:
            self.assertTrue(visit.doctor.full_name and visit.patient.name)

    def test_seed_uses_local_today_and_tomorrow_in_dashboard(self):
        call_command("seed_demo", stdout=StringIO())
        manager = get_user_model().objects.create_superuser("demo-manager")
        self.client.force_login(manager)
        for offset, day_filter in enumerate(("today", "tomorrow")):
            with self.subTest(day_filter=day_filter):
                response = self.client.get(
                    reverse("doctor_dashboard"), {"filter": day_filter}
                )
                self.assertEqual(response.status_code, 200)
                visits = list(response.context["appointments"])
                self.assertEqual(len(visits), 3)
                self.assertEqual(
                    {visit.doctor_id for visit in visits},
                    set(Doctor.objects.values_list("pk", flat=True)),
                )
                for visit in visits:
                    local = timezone.localtime(visit.date_time)
                    self.assertEqual(
                        local.date(), date(2030, 5, 2) + timedelta(days=offset)
                    )
                    self.assertIn(local.strftime("%H:%M"), dict(TIME_CHOICES))
                    self.assertEqual(visit.status, "planned")

    def test_seed_preserves_existing_data(self):
        patient = Patient.objects.create(name="Существующий пациент")
        with self.assertRaises(CommandError):
            call_command("seed_demo", stdout=StringIO())
        patient.refresh_from_db()
        self.assertEqual(patient.name, "Существующий пациент")
        self.assertEqual(Patient.objects.count(), 1)
        self.assertFalse(Doctor.objects.exists())
        self.assertFalse(Appointment.objects.exists())
