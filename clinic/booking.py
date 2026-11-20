from datetime import date, datetime
from functools import partial

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from .constants import TIME_CHOICES
from .models import Appointment, Doctor, Patient
from .notifications import notify_new_appointment


class SlotUnavailable(ValidationError):
    def __init__(self):
        super().__init__("На это время врач уже занят.")


def clinic_slot(day: date, time_slot: str) -> datetime:
    if time_slot not in dict(TIME_CHOICES):
        raise ValidationError("Выберите время из расписания.")
    value = timezone.make_aware(
        datetime.combine(day, datetime.strptime(time_slot, "%H:%M").time())
    )
    if value <= timezone.now():
        raise ValidationError("Выберите время в будущем.")
    return value


def is_slot_conflict(error):
    diagnostics = getattr(error.__cause__, "diag", None)
    return (
        getattr(diagnostics, "constraint_name", None)
        == "clinic_unique_occupied_doctor_slot"
    )


def book_appointment(
    *, doctor, day, time_slot, owner_name, owner_phone, pet_name, pet_species, complaint
) -> Appointment:
    try:
        with transaction.atomic():
            # Serialize booking and archiving decisions for this doctor.
            if (
                not Doctor.objects.select_for_update()
                .filter(pk=doctor.pk, is_active=True)
                .exists()
            ):
                raise ValidationError("Врач больше не принимает пациентов.")
            when = clinic_slot(day, time_slot)
            patients = list(
                Patient.objects.filter(
                    name=pet_name, owner_name=owner_name, owner_phone=owner_phone
                )[:2]
            )
            if len(patients) > 1 or (patients and patients[0].species != pet_species):
                raise ValidationError("Для записи обратитесь к администратору клиники.")
            patient = (
                patients[0]
                if patients
                else Patient.objects.create(
                    name=pet_name,
                    owner_name=owner_name,
                    owner_phone=owner_phone,
                    species=pet_species,
                )
            )
            visit = Appointment.objects.create(
                patient=patient, doctor=doctor, date_time=when, complaint=complaint
            )
            transaction.on_commit(
                partial(notify_new_appointment, visit.pk), robust=True
            )
            return visit
    except IntegrityError as error:
        if is_slot_conflict(error):
            raise SlotUnavailable() from error
        raise
