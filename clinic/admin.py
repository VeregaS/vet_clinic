from django.contrib import admin

from .models import Appointment, Doctor, MedicalRecord, Patient


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ("full_name", "specialization", "phone")
    search_fields = ("full_name",)


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ("name", "species", "owner_name")
    list_filter = ("species",)


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("date_time", "patient", "doctor", "status")
    list_filter = ("status", "date_time")


@admin.register(MedicalRecord)
class MedicalRecordAdmin(admin.ModelAdmin):
    list_display = ("patient", "doctor", "created_at")
