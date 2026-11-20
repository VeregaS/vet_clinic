from datetime import timedelta
from unittest.mock import patch
from urllib.error import HTTPError

from django.test import TestCase, override_settings
from django.utils import timezone

from clinic.models import Appointment, Doctor, Patient
from clinic.notifications import notify_new_appointment


@override_settings(TELEGRAM_BOT_TOKEN="demo-token")
class NotificationTests(TestCase):
    def setUp(self):
        self.doctor = Doctor.objects.create(telegram_id="123")
        self.visit = Appointment.objects.create(
            doctor=self.doctor,
            patient=Patient.objects.create(owner_name="PrivateOwner"),
            date_time=timezone.now() + timedelta(days=1),
        )

    @patch("clinic.notifications.urlopen")
    def test_post_and_missing_recipient(self, send):
        notify_new_appointment(self.visit.pk)
        req = send.call_args.args[0]
        self.assertEqual(req.get_method(), "POST")
        self.assertNotIn(b"PrivateOwner", req.data)
        self.assertEqual(send.call_args.kwargs["timeout"], 3)
        self.doctor.telegram_id = ""
        self.doctor.save()
        notify_new_appointment(self.visit.pk)
        self.assertEqual(send.call_count, 1)

    @patch("clinic.notifications.urlopen")
    def test_timeout_and_provider_error(self, send):
        for error in [
            TimeoutError("demo-token"),
            HTTPError("private", 403, "demo-token", {}, None),
        ]:
            send.side_effect = error
            with self.assertLogs("clinic.notifications") as log:
                notify_new_appointment(self.visit.pk)
            self.assertNotIn("demo-token", str(log.output))
            self.assertTrue(Appointment.objects.filter(pk=self.visit.pk).exists())
