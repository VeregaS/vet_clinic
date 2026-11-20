from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.db import close_old_connections, connections, transaction
from django.test import TransactionTestCase
from django.utils import timezone

from clinic.booking import SlotUnavailable, book_appointment, clinic_slot
from clinic.models import Appointment, Doctor, Patient


class BookingTests(TransactionTestCase):
    def setUp(self):
        self.doctor = Doctor.objects.create(full_name="A")
        self.day = timezone.localdate() + timedelta(days=2)
        self.data = dict(
            doctor=self.doctor,
            day=self.day,
            time_slot="10:30",
            owner_name="Demo",
            owner_phone="+79990000000",
            pet_name="Pet",
            pet_species="Кошка",
            complaint="Осмотр",
        )

    def test_concurrent_slot(self):
        start = Barrier(2)

        def run(name):
            close_old_connections()
            try:
                start.wait(timeout=10)
                book_appointment(**dict(self.data, pet_name=name))
                return True
            except SlotUnavailable:
                return False
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertCountEqual(pool.map(run, ["First", "Second"]), [True, False])
        self.assertEqual(Appointment.objects.count(), 1)
        self.assertEqual(Patient.objects.count(), 1)

    def test_cancel_then_rebook(self):
        first = book_appointment(**self.data)
        first.status = "canceled"
        first.save()
        second = book_appointment(**self.data)
        self.assertEqual(first.patient_id, second.patient_id)
        self.assertNotEqual(first.pk, second.pk)
        first.status = "planned"
        with self.assertRaises(ValidationError):
            first.full_clean()

    def test_distinct_doctor_and_ambiguous_patient(self):
        book_appointment(**self.data)
        other = Doctor.objects.create(full_name="B")
        book_appointment(**dict(self.data, doctor=other))
        with self.assertRaises(ValidationError):
            book_appointment(**dict(self.data, time_slot="11:30", pet_species="Собака"))

    def test_time_and_archive(self):
        self.assertEqual(clinic_slot(self.day, "08:30").utcoffset(), timedelta(hours=3))
        for day, slot in [(self.day, "08:00"), (self.day - timedelta(days=7), "18:30")]:
            with self.assertRaises(ValidationError):
                book_appointment(**dict(self.data, day=day, time_slot=slot))
        self.doctor.is_active = False
        self.doctor.save()
        with self.assertRaises(ValidationError):
            book_appointment(**self.data)

    @patch("clinic.booking.notify_new_appointment")
    def test_notify_after_commit_only(self, notify):
        with self.assertRaises(ValueError):
            with transaction.atomic():
                book_appointment(**self.data)
                raise ValueError()
        notify.assert_not_called()
        visit = book_appointment(**self.data)
        notify.assert_called_once_with(visit.pk)
