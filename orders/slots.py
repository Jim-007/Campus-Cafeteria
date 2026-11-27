"""Pickup time slots (FR5). Slots are created on demand for the next few hours."""
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .models import TimeSlot


def ensure_slots(now=None):
    """Create the upcoming slots if missing and return the ones students can pick."""
    now = timezone.localtime(now or timezone.now())
    length = timedelta(minutes=settings.SLOT_MINUTES)
    base = now.replace(second=0, microsecond=0)
    first = base + timedelta(minutes=settings.SLOT_MINUTES - base.minute % settings.SLOT_MINUTES)
    for i in range(settings.SLOT_COUNT):
        start = first + i * length
        TimeSlot.objects.get_or_create(
            start_time=start,
            defaults={'end_time': start + length, 'max_orders': settings.SLOT_MAX_ORDERS},
        )
    window_end = first + settings.SLOT_COUNT * length
    return list(TimeSlot.objects.filter(start_time__gt=now, start_time__lt=window_end))
