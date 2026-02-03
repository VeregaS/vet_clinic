from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView

from .forms import AppointmentForm
from .models import Appointment, Patient


class DoctorDashboardView(ListView):
    model = Appointment
    template_name = "clinic/doctor_dashboard.html"
    context_object_name = "appointments"
    ordering = ["-date_time"]


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
        # потом добавлю тг-уведомление?
        messages.success(
            self.request, f"Вы успешно записаны! Ждем Вас и {pet_name} :)."
        )
        return super().form_valid(form)
