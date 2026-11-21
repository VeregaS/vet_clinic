from datetime import datetime, timedelta
from datetime import timezone as dt_timezone
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import connection
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from clinic.models import Appointment, Doctor, Patient
from clinic.phones import normalize_phone


class WorkflowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            "employee", password="demo-only"
        )
        self.doc = Doctor.objects.create(full_name="Врач", user=self.user)
        self.day = timezone.localdate() + timedelta(days=1)
        self.data = dict(
            doctor=self.doc.pk,
            date=self.day,
            time_slot="18:30",
            owner_name="Владелец",
            owner_phone="8 (999) 000-00-00",
            pet_name="Кот",
            pet_species="Кошка",
            complaint="Осмотр",
        )

    def test_booking_and_download(self):
        self.assertRedirects(self.client.post("/", self.data), "/")
        response = self.client.post("/", self.data)
        self.assertContains(response, "уже занят")
        visit = Appointment.objects.get()
        self.assertEqual(visit.patient.owner_phone, normalize_phone("+7 999 000 00 00"))
        self.assertTrue(self.client.login(username="employee", password="demo-only"))
        self.assertEqual(
            self.client.post(
                reverse("appointment_edit", args=[visit.pk]),
                {
                    "status": "completed",
                    "diagnosis": "Готово",
                    "prescription": "Осмотр",
                },
            ).status_code,
            302,
        )
        visit.refresh_from_db()
        self.assertEqual(visit.status, "completed")
        visit.patient.name = 'Кот "Мурзик"'
        visit.patient.save()
        pdf = self.client.get(reverse("patient_pdf", args=[visit.patient_id]))
        self.assertEqual(pdf["Content-Type"], "application/pdf")
        self.assertTrue(pdf.content.startswith(b"%PDF-"))
        self.assertIn("no-store", pdf["Cache-Control"])
        for obj in [visit.patient, self.doc]:
            with self.assertRaises(ProtectedError):
                obj.delete()
        self.doc.is_active = False
        self.doc.save()
        self.assertFalse(
            self.client.get("/").context["form"].fields["doctor"].queryset.exists()
        )
        self.assertEqual(self.client.post(reverse("logout")).status_code, 302)
        self.assertEqual(self.client.get(reverse("doctor_dashboard")).status_code, 302)

    def test_schedule_midnight_and_pagination(self):
        instant = datetime(2030, 5, 1, 21, 10, tzinfo=dt_timezone.utc)
        patient = Patient.objects.create(name="Кот")
        for number in range(26):
            Appointment.objects.create(
                patient=patient,
                doctor=self.doc,
                date_time=instant + timedelta(minutes=number),
            )
        with patch("django.utils.timezone.now", return_value=instant):
            self.client.force_login(self.user)
            first = self.client.get(reverse("doctor_dashboard"), {"filter": "today"})
            self.assertEqual(len(first.context["appointments"]), 25)
            self.assertContains(first, "filter=today&amp;page=2")
            second = self.client.get(
                reverse("doctor_dashboard"), {"filter": "today", "page": 2}
            )
            self.assertEqual(len(second.context["appointments"]), 1)
            tomorrow = self.client.get(
                reverse("doctor_dashboard"), {"filter": "tomorrow"}
            )
            self.assertFalse(tomorrow.context["appointments"])

    def test_schedule_query_count_is_constant_per_page(self):
        manager = get_user_model().objects.create_superuser("schedule-manager")
        self.client.force_login(manager)
        dashboard = reverse("doctor_dashboard")
        start = timezone.now()
        patient = Patient.objects.create(name="Пациент 1")
        Appointment.objects.create(doctor=self.doc, patient=patient, date_time=start)

        with CaptureQueriesContext(connection) as single:
            response = self.client.get(dashboard)
        self.assertEqual(len(response.context["appointments"]), 1)

        for number in range(2, 26):
            doctor = Doctor.objects.create(full_name=f"Врач {number}")
            patient = Patient.objects.create(name=f"Пациент {number}")
            Appointment.objects.create(
                doctor=doctor,
                patient=patient,
                date_time=start + timedelta(minutes=number),
            )

        with self.assertNumQueries(len(single)):
            response = self.client.get(dashboard)
        self.assertEqual(len(response.context["appointments"]), 25)
        self.assertContains(response, "Пациент 25")
        self.assertContains(response, "Врач 25", count=2)
