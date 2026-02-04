from datetime import datetime, timedelta

from django import forms
from django.utils import timezone

from .constants import SPECIES_CHOICES, TIME_CHOICES
from .models import Appointment


class AppointmentForm(forms.ModelForm):
    owner_name = forms.CharField(
        max_length=50,
        help_text="Введите своё ФИО",
        label="ФИО",
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Ваше ФИО"}
        ),
    )
    owner_phone = forms.CharField(
        max_length=11,
        help_text="Введите свой номер телефона",
        label="Телефон",
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Телефон"}
        ),
    )
    pet_species = forms.ChoiceField(
        choices=SPECIES_CHOICES,
        help_text="Введите вид вашего питомца (кошка, собака и т.п.)",
        label="Вид питомца",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    pet_name = forms.CharField(
        max_length=15,
        help_text="Введите кличку вашего питомца",
        label="Кличка питомца",
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Кличка"}
        ),
    )
    date = forms.DateField(
        label="Дата приема",
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )

    time_slot = forms.ChoiceField(
        label="Время",
        choices=TIME_CHOICES,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    class Meta:
        model = Appointment
        fields = ["doctor", "complaint"]

        widgets = {
            "doctor": forms.Select(attrs={"class": "form-select"}),
            "complaint": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Опишите жалобу",
                }
            ),
        }

    def save(self, commit=True):
        appointment = super().save(commit=False)

        chosen_date = self.cleaned_data["date"]
        chosen_time_str = self.cleaned_data["time_slot"]

        chosen_time = datetime.strptime(chosen_time_str, "%H:%M").time()

        appointment.date_time = datetime.combine(chosen_date, chosen_time)

        if commit:
            appointment.save()
        return appointment

    def clean(self):
        cleaned_data = super().clean()
        doctor = cleaned_data.get("doctor")
        date = cleaned_data.get("date")
        time_str = cleaned_data.get("time_slot")
        date_time = None

        if date and time_str:
            t_obj = datetime.strptime(time_str, "%H:%M").time()
            date_time = datetime.combine(date, t_obj)

        if not doctor or not date_time:
            return

        if date_time < datetime.now():
            self.add_error(
                "date",
                "Невозможно записаться на прошлую дату!",
            )

        collision = Appointment.objects.filter(
            doctor=doctor, date_time=date_time
        ).exists()

        if collision:
            self.add_error(
                "time_slot",
                "На это время врач уже занят! Пожалуйста, выберите другой час.",
            )

        return cleaned_data
