import datetime

import weasyprint
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.http import content_disposition_header
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DetailView, FormView, ListView, UpdateView

from .access import can_manage, visible_appointments, visible_patients
from .booking import SlotUnavailable, book_appointment, is_slot_conflict
from .forms import AppointmentForm, DoctorAppointmentForm, DoctorForm, PatientForm
from .models import Appointment, Doctor, Patient


class DoctorsContext(LoginRequiredMixin):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if can_manage(self.request.user):
            context.update(
                doctors_list=Doctor.objects.order_by("full_name"),
                doctor_form=DoctorForm(),
            )
        return context


class DoctorDashboardView(DoctorsContext, ListView):
    template_name = "clinic/doctor_dashboard.html"
    context_object_name = "appointments"
    paginate_by = 25

    def get_queryset(self):
        qs = visible_appointments(self.request.user).order_by("date_time", "pk")
        doctor_id = self.request.session.get("doctor_id")
        if doctor_id and can_manage(self.request.user):
            qs = qs.filter(doctor_id=doctor_id)
        day_filter = self.request.GET.get("filter")
        if day_filter in ("today", "tomorrow"):
            day = timezone.localdate() + datetime.timedelta(
                days=int(day_filter == "tomorrow")
            )
            qs = qs.filter(date_time__date=day)
        return qs

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            current_filter=self.request.GET.get("filter", "all"), **kwargs
        )


@login_required
@permission_required("clinic.manage_clinic", raise_exception=True)
@require_POST
def set_doctor_session(request, doctor_id):
    if doctor_id:
        doctor = get_object_or_404(Doctor, pk=doctor_id)
        request.session["doctor_id"] = doctor.pk
        request.session["doctor_name"] = doctor.full_name
    else:
        request.session.pop("doctor_id", None)
        request.session.pop("doctor_name", None)
    return redirect("doctor_dashboard")


class DoctorCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    permission_required = "clinic.manage_clinic"
    model = Doctor
    form_class = DoctorForm
    template_name = "clinic/doctor_form.html"
    success_url = reverse_lazy("doctor_dashboard")


class PatientDetailView(DoctorsContext, DetailView):
    template_name = "clinic/patient_detail.html"
    context_object_name = "patient"

    def get_queryset(self):
        return visible_patients(self.request.user)

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            history=visible_appointments(self.request.user).filter(patient=self.object),
            **kwargs,
        )


class PatientUpdateView(DoctorsContext, PermissionRequiredMixin, UpdateView):
    permission_required = "clinic.manage_clinic"
    model = Patient
    form_class = PatientForm
    template_name = "clinic/patient_form.html"

    def get_success_url(self):
        return reverse_lazy("patient_detail", kwargs={"pk": self.object.pk})


@login_required
def patient_pdf_view(request, pk):
    patient = get_object_or_404(visible_patients(request.user), pk=pk)
    history = visible_appointments(request.user).filter(patient=patient)
    html = render_to_string(
        "clinic/patient_pdf.html", {"patient": patient, "history": history}
    )
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = content_disposition_header(
        False, f"card_{patient.pk}.pdf"
    )
    weasyprint.HTML(string=html).write_pdf(response)
    return response


class AppointmentUpdateView(DoctorsContext, UpdateView):
    form_class = DoctorAppointmentForm
    template_name = "clinic/appointment_form.html"
    success_url = reverse_lazy("doctor_dashboard")

    def get_queryset(self):
        return visible_appointments(self.request.user)

    def form_valid(self, form):
        try:
            with transaction.atomic():
                return super().form_valid(form)
        except IntegrityError as error:
            if not is_slot_conflict(error):
                raise
            form.add_error("status", SlotUnavailable())
            return self.form_invalid(form)


class PatientListView(DoctorsContext, ListView):
    template_name = "clinic/patient_list.html"
    context_object_name = "patients"
    paginate_by = 25

    def get_queryset(self):
        qs = visible_patients(self.request.user).order_by("name", "pk")
        query = self.request.GET.get("q")
        if query:
            qs = qs.filter(
                Q(name__icontains=query)
                | Q(owner_name__icontains=query)
                | Q(owner_phone__icontains=query)
            )
        return qs


class HomeView(FormView):
    template_name = "clinic/home.html"
    form_class = AppointmentForm
    success_url = reverse_lazy("home")

    def form_valid(self, form):
        data = dict(form.cleaned_data)
        data["day"] = data.pop("date")
        try:
            book_appointment(**data)
        except SlotUnavailable as error:
            form.add_error("time_slot", error)
            return self.form_invalid(form)
        except ValidationError as error:
            form.add_error(None, error)
            return self.form_invalid(form)
        messages.success(self.request, "Вы успешно записаны!")
        return super().form_valid(form)
