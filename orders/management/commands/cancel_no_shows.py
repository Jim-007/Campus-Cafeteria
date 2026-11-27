"""Cancel orders that were not collected within the grace period after their slot started."""
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from orders.models import Order
from orders.services import cancel_order


class Command(BaseCommand):
    """Run this every few minutes (or before the demo) to release no-show orders."""

    help = 'Cancel orders not collected within the grace period'

    def handle(self, *args, **options):
        limit = timezone.now() - timedelta(minutes=settings.NO_SHOW_GRACE_MINUTES)
        late = Order.objects.filter(slot__start_time__lt=limit).exclude(
            status__in=[Order.COLLECTED, Order.CANCELLED])
        for order in late:
            cancel_order(order, 'No-show: not collected in time')
        self.stdout.write(self.style.SUCCESS(f'{late.count()} no-show orders cancelled.'))
