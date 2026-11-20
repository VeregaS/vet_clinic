from django import forms
from django.core.exceptions import ValidationError

from .booking import clinic_slot
from .constants import SPECIES_CHOICES, TIME_CHOICES
from .models import Appointment, Doctor, Patient
from .phones import normalize_phone


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
        max_length=20,
        help_text="Введите свой номер телефона",
        label="Телефон",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "+7 (999) 000-00-00",
                "type": "tel",
                "id": "phone-mask",
            }
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
        widget=forms.DateInput(
            attrs={"class": "form-control", "type": "date", "placeholder": "дд.мм.гггг"}
        ),
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["doctor"].queryset = Doctor.objects.filter(is_active=True).order_by(
            "full_name"
        )

    def clean_owner_phone(self):
        return normalize_phone(self.cleaned_data["owner_phone"])

    def clean(self):
        data = super().clean()
        if data.get("date") and data.get("time_slot"):
            try:
                clinic_slot(data["date"], data["time_slot"])
            except ValidationError as error:
                self.add_error("date", error)
        return data


class PatientForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = ["name", "species", "breed", "birth_date", "owner_name", "owner_phone"]
        labels = {
            "name": "Кличка",
            "species": "Вид",
            "breed": "Порода",
            "birth_date": "Дата рождения",
            "owner_name": "Владелец",
            "owner_phone": "Телефон",
        }
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "species": forms.Select(
                choices=SPECIES_CHOICES, attrs={"class": "form-select"}
            ),
            "breed": forms.TextInput(attrs={"class": "form-control"}),
            "birth_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "owner_name": forms.TextInput(attrs={"class": "form-control"}),
            "owner_phone": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "+7 (999) 000-00-00",
                    "type": "tel",
                    "id": "phone-mask",
                }
            ),
        }

    def clean_owner_phone(self):
        return normalize_phone(self.cleaned_data["owner_phone"])


class DoctorAppointmentForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ["diagnosis", "prescription", "status"]
        labels = {
            "diagnosis": "Поставленный диагноз",
            "prescription": "Назначения / Рецепт",
            "status": "Статус визита",
        }
        widgets = {
            "diagnosis": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Опишите диагноз...",
                }
            ),
            "prescription": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Список лекарств и рекомендаций...",
                }
            ),
            "status": forms.Select(attrs={"class": "form-select"}),
        }


class DoctorForm(forms.ModelForm):
    class Meta:
        model = Doctor
        fields = ["full_name", "specialization", "phone", "telegram_id"]
        labels = {
            "full_name": "ФИО врача",
            "specialization": "Специализация",
            "phone": "Телефон",
            "telegram_id": "Telegram id для оповещения о новых записях",
        }
        widgets = {
            "full_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Иванов Иван Иванович"}
            ),
            "specialization": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Хирург"}
            ),
            "phone": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "+7 (999) 000-00-00",
                    "type": "tel",
                    "id": "phone-mask",
                }
            ),
            "telegram_id": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "123456789"}
            ),
        }
