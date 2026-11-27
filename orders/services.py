"""Business rules for orders, payments and status changes.

Views call these functions so the rules live in one place (service layer).
"""
import uuid

from django.db import transaction
from django.utils import timezone

from kitchen.notifications import notify, notify_staff
from menu.models import MenuItem
from .models import Order, OrderItem, Payment, TimeSlot

ONLINE_METHODS = [Payment.CARD, Payment.BKASH, Payment.NAGAD, Payment.ROCKET]

# Which status an order may move to next.
ALLOWED = {
    Order.PLACED: {Order.ACCEPTED, Order.CANCELLED},
    Order.ACCEPTED: {Order.PREPARING, Order.CANCELLED},
    Order.PREPARING: {Order.READY, Order.CANCELLED},
    Order.READY: {Order.COLLECTED, Order.CANCELLED},
    Order.COLLECTED: set(),
    Order.CANCELLED: set(),
}


class OrderError(Exception):
    """Raised when a rule stops an order action. The message is safe to show the user."""


@transaction.atomic
def place_order(user, lines, slot, method, instructions=''):
    """Create an order from cart lines (FR4, FR5, FR7).

    Checks the slot and stock, saves the order, lowers the stock and starts the payment.
    Counter payments are visible to staff straight away; online ones wait until paid.
    """
    if not lines:
        raise OrderError('Your cart is empty.')
    if method not in dict(Payment.METHODS):
        raise OrderError('Choose a payment method.')
    slot = TimeSlot.objects.select_for_update().get(pk=slot.pk)
    if slot.start_time <= timezone.now():
        raise OrderError('That pickup time has passed. Choose another slot.')
    if slot.is_full:
        raise OrderError('That pickup slot is full. Choose another slot.')

    order = Order.objects.create(user=user, slot=slot, special_instructions=instructions[:200])
    total = 0
    for line in lines:
        item = MenuItem.objects.select_for_update().get(pk=line['item'].pk)
        qty = line['quantity']
        if not item.can_order or item.stock < qty:
            raise OrderError(f'{item.name} is sold out or has less than {qty} left.')
        item.stock -= qty
        item.save(update_fields=['stock'])
        OrderItem.objects.create(order=order, item=item, quantity=qty, unit_price=item.price)
        total += item.price * qty

    online = method in ONLINE_METHODS
    Payment.objects.create(order=order, method=method, amount=total,
                           status=Payment.PROCESSING if online else Payment.PENDING)
    if not online:
        notify_staff(f'New order #{order.pk} for {slot}.', order)
    return order


@transaction.atomic
def pay_order(order, success):
    """Finish a simulated online payment (FR7). A failure cancels the order."""
    payment = order.payment
    if payment.status != Payment.PROCESSING:
        raise OrderError('This payment is not waiting for a result.')
    if success:
        payment.status = Payment.PAID
        payment.transaction_ref = f'SIM-{order.pk}-{uuid.uuid4().hex[:8].upper()}'
        payment.save()
        notify(order.user, f'Payment received for order #{order.pk}.', order)
        notify_staff(f'New order #{order.pk} for {order.slot}.', order)
    else:
        cancel_order(order, 'Payment failed')


@transaction.atomic
def change_status(order, new_status):
    """Move an order forward (FR9) and tell the student (FR11)."""
    order = Order.objects.select_for_update().get(pk=order.pk)
    if new_status not in ALLOWED[order.status]:
        raise OrderError(f'An order that is {order.get_status_display()} cannot become '
                         f'{dict(Order.STATUSES)[new_status]}.')
    order.status = new_status
    order.save()
    if new_status == Order.COLLECTED and order.payment.status == Payment.PENDING:
        order.payment.status = Payment.PAID  # cash taken at the counter
        order.payment.save()
    notify(order.user, f'Order #{order.pk} is now {order.get_status_display()}.', order)
    return order


@transaction.atomic
def cancel_order(order, reason=''):
    """Cancel an order, return the stock and refund a paid payment (FR9, FR12)."""
    order = Order.objects.select_for_update().get(pk=order.pk)
    if Order.CANCELLED not in ALLOWED[order.status]:
        raise OrderError(f'An order that is {order.get_status_display()} cannot be cancelled.')
    for line in order.lines.select_related('item'):
        line.item.stock += line.quantity
        line.item.save(update_fields=['stock'])
    payment = order.payment
    if payment.status == Payment.PAID:
        payment.status = Payment.REFUNDED
        payment.save()
    elif payment.status == Payment.PROCESSING:
        payment.status = Payment.FAILED
        payment.save()
    order.status = Order.CANCELLED
    order.cancel_reason = reason[:200]
    order.save()
    notify(order.user, f'Order #{order.pk} was cancelled. Reason: {reason or "not given"}.', order)
    return order
