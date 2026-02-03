from datetime import timedelta

from django import forms
from django.utils import timezone

from .models import Appointment


class AppointmentForm(forms.ModelForm):
    SPECIES_CHOICES = [
        ("dog", "Собака"),
        ("cat", "Кошка"),
        ("parrot", "Попугай"),
        ("hamster", "Хомяк"),
        ("snake", "Змея"),
        ("other", "Другое"),
    ]

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

    class Meta:
        model = Appointment

        fields = ["doctor", "date_time", "complaint"]

        widgets = {
            "doctor": forms.Select(attrs={"class": "form-select"}),
            "date_time": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"}
            ),
            "complaint": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Опишите жалобу",
                }
            ),
        }

    def clean_date_time(self):
        data = self.cleaned_data["date_time"]
        if data < timezone.now():
            raise forms.ValidationError("Нельзя записаться на прошлую дату!")
        return data

    def clean(self):
        cleaned_data = super().clean()
        doctor = cleaned_data.get("doctor")
        date_time = cleaned_data.get("date_time")

        if not doctor or not date_time:
            return

        if date_time.minute != 30:
            self.add_error(
                "date_time",
                "Запись возможна только на половину часа (8:30, 9:30, 10:30 и т.д.)",
            )

        collision = Appointment.objects.filter(
            doctor=doctor, date_time=date_time
        ).exists()

        if collision:
            self.add_error(
                "date_time",
                "На это время врач уже занят! Пожалуйста, выберите другой час.",
            )

        return cleaned_data
