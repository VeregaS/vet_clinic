import datetime
import os
import urllib.parse
import urllib.request

import weasyprint
from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from .forms import AppointmentForm, DoctorAppointmentForm, DoctorForm, PatientForm
from .models import Appointment, Doctor, Patient


class DoctorsContext:
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["doctors_list"] = Doctor.objects.all()
        context["doctor_form"] = DoctorForm()
        return context


class DoctorDashboardView(DoctorsContext, ListView):
    model = Appointment
    template_name = "clinic/doctor_dashboard.html"
    context_object_name = "appointments"
    ordering = ["date_time"]

    def get_queryset(self):
        qs = super().get_queryset()
        doctor_id = self.request.session.get("doctor_id")
        if doctor_id:
            qs = qs.filter(doctor_id=doctor_id)

        filter_param = self.request.GET.get("filter")
        today = datetime.date.today()

        if filter_param == "today":
            qs = qs.filter(date_time__date=today)
        elif filter_param == "tomorrow":
            tomorrow = today + datetime.timedelta(days=1)
            qs = qs.filter(date_time__date=tomorrow)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["current_filter"] = self.request.GET.get("filter", "all")
        return context


def set_doctor_session(request, doctor_id):
    doctor = get_object_or_404(Doctor, pk=doctor_id)
    request.session["doctor_id"] = doctor.id
    request.session["doctor_name"] = doctor.full_name
    return redirect("doctor_dashboard")


class DoctorCreateView(CreateView):
    model = Doctor
    form_class = DoctorForm
    success_url = reverse_lazy("doctor_dashboard")


class PatientDetailView(DoctorsContext, DetailView):
    model = Patient
    template_name = "clinic/patient_detail.html"
    context_object_name = "patient"


class PatientUpdateView(DoctorsContext, UpdateView):
    model = Patient
    form_class = PatientForm
    template_name = "clinic/patient_form.html"

    def get_success_url(self):
        return reverse_lazy("patient_detail", kwargs={"pk": self.object.pk})


def patient_pdf_view(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    history = Appointment.objects.filter(patient=patient).order_by("-date_time")
    html_string = render_to_string(
        "clinic/patient_pdf.html",
        {
            "patient": patient,
            "history": history,
        },
    )
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="card_{patient.name}.pdf"'

    weasyprint.HTML(string=html_string).write_pdf(response)

    return response


class AppointmentUpdateView(DoctorsContext, UpdateView):
    model = Appointment
    form_class = DoctorAppointmentForm
    template_name = "clinic/appointment_form.html"

    def get_success_url(self):
        return reverse_lazy("doctor_dashboard")


class PatientListView(DoctorsContext, ListView):
    model = Patient
    template_name = "clinic/patient_list"
    context_object_name = "patients"

    def get_queryset(self):
        qs = super().get_queryset()
        query = self.request.GET.get("q")
        if query:
            qs = Patient.objects.filter(
                Q(name__icontains=query)
                | Q(owner_name__icontains=query)
                | Q(owner_phone__icontains=query)
            )
        return qs


class HomeView(CreateView):
    template_name = "clinic/home.html"
    success_url = reverse_lazy("home")

    form_class = AppointmentForm

    def form_valid(self, form):
        owner_name = form.cleaned_data["owner_name"]
        owner_phone = form.cleaned_data["owner_phone"]
        pet_species = form.cleaned_data["pet_species"]
        pet_name = form.cleaned_data["pet_name"]

        patient, created = Patient.objects.get_or_create(
            name=pet_name,
            owner_name=owner_name,
            owner_phone=owner_phone,
            defaults={"owner_phone": owner_phone, "species": pet_species},
        )

        appointment = form.save(commit=False)
        appointment.patient = patient
        appointment.save()

        doctor = appointment.doctor

        tg_msg = (
            f"⚡ Новая запись к Вам!\n"
            f"📅 {appointment.date_time.strftime('%d.%m %H:%M')}\n"
            f"👤 {owner_name} ({owner_phone})\n"
            f"🐾 {pet_name} ({pet_species})"
        )

        send_telegram_message(doctor.telegram_id, tg_msg)

        messages.success(self.request, f"Вы успешно записаны! Ждем Вас и {pet_name} :)")
        return super().form_valid(form)


def send_telegram_message(chat_id, message):
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")

    if not bot_token or not chat_id:
        print("⚠️ Ошибка: Нет токена телеграм или ID врача")
        return

    base_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    params = urllib.parse.urlencode({"chat_id": chat_id, "text": message})
    url = f"{base_url}?{params}"

    try:
        urllib.request.urlopen(url)
    except Exception as e:
        print(f"Ошибка отправки: {e}")
