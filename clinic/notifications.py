import logging
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.utils import timezone

from .models import Appointment

logger = logging.getLogger(__name__)


def notify_new_appointment(appointment_id: int) -> None:
    if not settings.TELEGRAM_BOT_TOKEN:
        return
    appointment = Appointment.objects.select_related("doctor").get(pk=appointment_id)
    if not appointment.doctor.telegram_id:
        return
    local_time = timezone.localtime(appointment.date_time)
    data = urlencode(
        {
            "chat_id": appointment.doctor.telegram_id,
            "text": f"Новая запись на {local_time:%d.%m.%Y %H:%M}",
        }
    ).encode()
    request = Request(
        f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
        data=data,
    )
    try:
        with urlopen(request, timeout=3):
            pass
    except OSError as error:
        logger.warning(
            "Telegram delivery failed for appointment %s (%s)",
            appointment_id,
            type(error).__name__,
        )
