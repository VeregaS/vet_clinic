from django.urls import path

from . import views

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("doctor/", views.DoctorDashboardView.as_view(), name="doctor_dashboard"),
    path("doctor/add/", views.DoctorCreateView.as_view(), name="doctor_add"),
    path("set-doctor/<int:doctor_id>/", views.set_doctor_session, name="set_doctor"),
    path("patients/", views.PatientListView.as_view(), name="patient_list"),
    path("patient/<int:pk>/", views.PatientDetailView.as_view(), name="patient_detail"),
    path(
        "patient/<int:pk>/edit/", views.PatientUpdateView.as_view(), name="patient_edit"
    ),
    path("patient/<int:pk>/pdf/", views.patient_pdf_view, name="patient_pdf"),
    path(
        "appointment/<int:pk>/examine/",
        views.AppointmentUpdateView.as_view(),
        name="appointment_edit",
    ),
]
