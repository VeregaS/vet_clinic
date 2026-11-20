from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from clinic.models import Appointment, Doctor, Patient


class AccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user("doctor")
        cls.other = get_user_model().objects.create_user("other")
        cls.admin = get_user_model().objects.create_superuser("manager")
        cls.doctor = Doctor.objects.create(full_name="A", user=cls.user)
        cls.second = Doctor.objects.create(full_name="B", user=cls.other)
        cls.shared = Patient.objects.create(name="Shared")
        cls.private = Patient.objects.create(name="Private")
        now = timezone.now()
        cls.own = Appointment.objects.create(
            doctor=cls.doctor, patient=cls.shared, date_time=now, diagnosis="mine"
        )
        cls.hidden = Appointment.objects.create(
            doctor=cls.second, patient=cls.shared, date_time=now, diagnosis="other-note"
        )
        Appointment.objects.create(
            doctor=cls.second, patient=cls.private, date_time=now + timedelta(days=1)
        )

    def test_guest_requires_login(self):
        routes = [
            ("doctor_dashboard", []),
            ("doctor_add", []),
            ("patient_list", []),
            ("patient_pdf", [self.shared.pk]),
            ("patient_detail", [self.shared.pk]),
            ("patient_edit", [self.shared.pk]),
            ("appointment_edit", [self.own.pk]),
        ]
        for name, args in routes:
            with self.subTest(name=name):
                self.assertEqual(
                    self.client.get(reverse(name, args=args)).status_code, 302
                )

    def test_scoped_reads_and_writes(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("patient_list"), {"q": "Private"})
        self.assertEqual(list(response.context["patients"]), [])
        detail = self.client.get(reverse("patient_detail", args=[self.shared.pk]))
        self.assertContains(detail, "mine")
        self.assertNotContains(detail, "other-note")
        with patch("clinic.views.weasyprint.HTML", autospec=True) as pdf:
            self.assertEqual(
                self.client.get(
                    reverse("patient_pdf", args=[self.shared.pk])
                ).status_code,
                200,
            )
            html = pdf.call_args.kwargs["string"]
            self.assertIn("mine", html)
            self.assertNotIn("other-note", html)
        for route in ("patient_detail", "patient_pdf"):
            self.assertEqual(
                self.client.get(reverse(route, args=[self.private.pk])).status_code, 404
            )
        self.assertEqual(
            self.client.post(
                reverse("appointment_edit", args=[self.hidden.pk]),
                {"status": "completed"},
            ).status_code,
            404,
        )
        self.hidden.refresh_from_db()
        self.assertEqual(self.hidden.status, "planned")
        self.assertEqual(
            self.client.post(
                reverse("patient_edit", args=[self.shared.pk])
            ).status_code,
            403,
        )
        self.assertEqual(self.client.post(reverse("doctor_add")).status_code, 403)
        self.assertEqual(
            self.client.post(reverse("set_doctor", args=[self.second.pk])).status_code,
            403,
        )

    def test_clinic_manager_without_admin_site_access(self):
        manager = get_user_model().objects.create_user("reception")
        manager.groups.add(Group.objects.get(name="Администраторы клиники"))
        self.client.force_login(manager)
        self.assertContains(self.client.get(reverse("patient_list")), "Private")
        response = self.client.post(
            reverse("doctor_add"), {"full_name": "C", "specialization": "Осмотр"}
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Doctor.objects.filter(full_name="C").exists())
        self.assertFalse(manager.is_staff)
        self.assertEqual(self.client.get(reverse("admin:index")).status_code, 302)

    def test_admin_and_profileless(self):
        self.client.force_login(self.admin)
        self.assertContains(
            self.client.get(reverse("patient_detail", args=[self.shared.pk])),
            "other-note",
        )
        self.assertEqual(
            self.client.get(reverse("set_doctor", args=[self.second.pk])).status_code,
            405,
        )
        user = get_user_model().objects.create_user("unlinked")
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("doctor_dashboard")).status_code, 403)
