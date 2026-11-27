"""Shared order models used by FR4 to FR12.

These models are the contract between the team members, so agree before
changing field names or status values.
"""
from django.conf import settings
from django.db import models

from menu.models import MenuItem


class TimeSlot(models.Model):
    """A 30-minute pickup window with a maximum number of orders (FR5)."""

    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    max_orders = models.PositiveIntegerField(default=10)

    class Meta:
        ordering = ['start_time']

    def __str__(self):
        return f'{self.start_time:%d %b %H:%M} - {self.end_time:%H:%M}'

    @property
    def booked(self):
        """Number of active orders in this slot."""
        return self.orders.exclude(status=Order.CANCELLED).count()

    @property
    def remaining(self):
        """How many more orders this slot can take."""
        return max(self.max_orders - self.booked, 0)

    @property
    def is_full(self):
        """True when the slot has reached its maximum number of orders."""
        return self.booked >= self.max_orders


class Order(models.Model):
    """A customer order (FR4, FR9, FR11)."""

    PLACED = 'placed'
    ACCEPTED = 'accepted'
    PREPARING = 'preparing'
    READY = 'ready'
    COLLECTED = 'collected'
    CANCELLED = 'cancelled'
    STATUSES = [
        (PLACED, 'Placed'),
        (ACCEPTED, 'Accepted'),
        (PREPARING, 'Preparing'),
        (READY, 'Ready for Pickup'),
        (COLLECTED, 'Collected'),
        (CANCELLED, 'Cancelled'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='orders')
    slot = models.ForeignKey(TimeSlot, on_delete=models.PROTECT, related_name='orders')
    status = models.CharField(max_length=10, choices=STATUSES, default=PLACED)
    special_instructions = models.CharField(max_length=200, blank=True)
    cancel_reason = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Order #{self.pk} ({self.get_status_display()})'

    @property
    def total(self):
        """Sum of all line totals."""
        return sum(line.line_total for line in self.lines.all())

    @property
    def progress(self):
        """Steps for the tracking bar. Empty when the order was cancelled."""
        flow = [self.PLACED, self.ACCEPTED, self.PREPARING, self.READY, self.COLLECTED]
        if self.status not in flow:
            return []
        names = dict(self.STATUSES)
        current = flow.index(self.status)
        return [{'label': names[step], 'state': 'done' if i < current else 'current' if i == current else 'todo'}
                for i, step in enumerate(flow)]

    @property
    def is_finished(self):
        """True when the order can not change any more."""
        return self.status in (self.COLLECTED, self.CANCELLED)


class OrderItem(models.Model):
    """One line of an order. unit_price keeps the price at the time of ordering."""

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='lines')
    item = models.ForeignKey(MenuItem, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=7, decimal_places=2)

    @property
    def line_total(self):
        """Quantity multiplied by the unit price."""
        return self.quantity * self.unit_price


class Payment(models.Model):
    """Payment for an order (FR7)."""

    BKASH, NAGAD, ROCKET, CARD, COUNTER = 'bkash', 'nagad', 'rocket', 'card', 'counter'
    METHODS = [
        (CARD, 'Visa / Mastercard'),
        (BKASH, 'bKash'),
        (NAGAD, 'Nagad'),
        (ROCKET, 'Rocket'),
        (COUNTER, 'Pay at counter'),
    ]
    PENDING, PROCESSING, PAID, FAILED, REFUNDED = 'pending', 'processing', 'paid', 'failed', 'refunded'
    STATUSES = [
        (PENDING, 'Pending'),
        (PROCESSING, 'Processing'),
        (PAID, 'Paid'),
        (FAILED, 'Failed'),
        (REFUNDED, 'Refunded'),
    ]

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='payment')
    method = models.CharField(max_length=10, choices=METHODS)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUSES, default=PENDING)
    transaction_ref = models.CharField(max_length=60, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.get_method_display()} - {self.get_status_display()}'
