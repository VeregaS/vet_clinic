from django.conf import settings
from django.db import models


class Doctor(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clinic_doctor",
    )
    is_active = models.BooleanField("Принимает пациентов", default=True)
    full_name = models.CharField("ФИО Врача", max_length=150)
    specialization = models.CharField("Специализация", max_length=100)
    phone = models.CharField("Телефон", max_length=20, blank=True)
    telegram_id = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Узнать свой ID можно у бота @userinfobot",
    )

    class Meta:
        permissions = [("manage_clinic", "Управление клиникой")]
        verbose_name = "Врач"
        verbose_name_plural = "Врачи"

    def __str__(self):
        return f"{self.full_name} ({self.specialization})"


class Patient(models.Model):
    name = models.CharField("Кличка", max_length=100)
    species = models.CharField("Вид животного", max_length=50)
    breed = models.CharField("Порода", max_length=100, blank=True)
    birth_date = models.DateField("Дата рождения", null=True, blank=True)

    owner_name = models.CharField("ФИО Владельца", max_length=150)
    owner_phone = models.CharField("Телефон владельца", max_length=20)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Пациент"
        verbose_name_plural = "Пациенты"

    def __str__(self):
        return f"{self.name} ({self.species}) - {self.owner_name}"


class Appointment(models.Model):
    STATUS_CHOICES = [
        ("planned", "Запланировано"),
        ("completed", "Завершено"),
        ("canceled", "Отменено"),
    ]

    doctor = models.ForeignKey(Doctor, on_delete=models.PROTECT, verbose_name="Врач")
    patient = models.ForeignKey(
        Patient,
        on_delete=models.PROTECT,
        verbose_name="Пациент",
        related_name="history",
    )
    date_time = models.DateTimeField("Дата и время приема")
    complaint = models.TextField("Жалоба", blank=True)
    diagnosis = models.TextField("Диагноз", blank=True, default="")
    prescription = models.TextField("Назначения / Рецепт", blank=True, default="")
    status = models.CharField(
        "Статус", max_length=20, choices=STATUS_CHOICES, default="planned"
    )

    class Meta:
        verbose_name = "Запись на прием"
        verbose_name_plural = "Записи на прием"
        ordering = ["-date_time", "pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["doctor", "date_time"],
                condition=models.Q(status__in=["planned", "completed"]),
                name="clinic_unique_occupied_doctor_slot",
                violation_error_message="Время уже занято.",
            )
        ]

    def __str__(self):
        return f"{self.date_time.strftime('%d.%m %H:%M')} - {self.patient.name}"
