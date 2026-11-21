from datetime import datetime, time, timedelta

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from clinic.models import Appointment, Doctor, Patient

# Doctor and patient IDs refer to the initial_data fixture.
VISITS = (
    (0, 6, 18, time(9, 30), "Паническая атака при виде призраков."),
    (0, 7, 19, time(11, 30), "Ненавидит понедельники, агрессия к собакам."),
    (0, 8, 20, time(15, 30), "Постоянно застревает в заборах и на крышах."),
    (1, 6, 21, time(9, 30), "Съел 50 кг рыбы за раз."),
    (1, 7, 19, time(11, 30), "Повторный приём."),
    (1, 8, 22, time(15, 30), "Проблемы с агрессией."),
)


class Command(BaseCommand):
    help = "Загрузить демоданные на сегодня и завтра в пустую базу клиники."

    @transaction.atomic
    def handle(self, *args, **options):
        if (
            Doctor.objects.exists()
            or Patient.objects.exists()
            or Appointment.objects.exists()
        ):
            raise CommandError(
                "В базе уже есть данные клиники. Используйте пустую демонстрационную БД."
            )

        now = timezone.localtime()
        today = now.date()
        tomorrow = today + timedelta(days=1)
        call_command("loaddata", "initial_data", verbosity=0)

        visits = []
        for day_offset, doctor_id, patient_id, slot, complaint in VISITS:
            day = today if day_offset == 0 else tomorrow
            start = datetime.combine(day, slot, tzinfo=now.tzinfo)
            completed = start <= now
            visits.append(
                Appointment(
                    doctor_id=doctor_id,
                    patient_id=patient_id,
                    date_time=start,
                    complaint=complaint,
                    status="completed" if completed else "planned",
                    diagnosis="Проведён осмотр." if completed else "",
                    prescription="Наблюдение." if completed else "",
                )
            )
        Appointment.objects.bulk_create(visits)
        self.stdout.write(
            self.style.SUCCESS(
                f"Создано демовизитов: {len(visits)} на {today:%d.%m.%Y} "
                f"и {tomorrow:%d.%m.%Y} ({now.tzinfo})."
            )
        )
