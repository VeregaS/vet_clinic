from django.core.exceptions import PermissionDenied

from .models import Appointment, Doctor, Patient


def can_manage(user):
    return user.is_active and user.has_perm("clinic.manage_clinic")


def staff_allowed(user):
    return can_manage(user) or (
        user.is_active and Doctor.objects.filter(user=user, is_active=True).exists()
    )


def visible_appointments(user):
    if not staff_allowed(user):
        raise PermissionDenied
    visits = Appointment.objects.select_related("doctor", "patient")
    return visits if can_manage(user) else visits.filter(doctor__user=user)


def visible_patients(user):
    visits = visible_appointments(user)
    if can_manage(user):
        return Patient.objects.all()
    return Patient.objects.filter(pk__in=visits.values("patient_id"))
