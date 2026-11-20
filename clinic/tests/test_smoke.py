from django.test import TestCase

from clinic.models import Appointment


class DemoTests(TestCase):
    fixtures = ["initial_data"]

    def test_home_displays_booking_form(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        for field in ("doctor", "date", "time_slot", "owner_phone"):
            self.assertIn(field, response.context["form"].fields)

    def test_initial_data_links_appointments(self):
        visits = list(Appointment.objects.select_related("doctor", "patient"))
        self.assertTrue(visits)
        for visit in visits:
            self.assertTrue(visit.doctor.full_name and visit.patient.name)
