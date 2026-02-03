import os
import urllib.parse
import urllib.request

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

        doctor = appointment.doctor

        tg_msg = (
            f"⚡ Новая запись к Вам!\n"
            f"📅 {appointment.date_time.strftime('%d.%m %H:%M')}\n"
            f"👤 {owner_name} ({owner_phone})\n"
            f"🐾 {pet_name} ({pet_species})"
        )

        send_telegram_message(doctor.telegram_id, tg_msg)

        messages.success(
            self.request, f"Вы успешно записаны! Ждем Вас и {pet_name} :)."
        )
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
