"""Staff order queue (FR9, FR10) and notifications for everyone (FR10, FR11)."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from orders import services
from orders.models import Order, Payment
from orders.services import OrderError
from .models import Notification

ACTIONS = {
    'accept': Order.ACCEPTED,
    'prepare': Order.PREPARING,
    'ready': Order.READY,
    'collect': Order.COLLECTED,
}


def kitchen_orders():
    """Orders staff must handle: paid online or pay-at-counter, not finished."""
    return (Order.objects
            .filter(payment__status__in=[Payment.PAID, Payment.PENDING])
            .exclude(status__in=[Order.COLLECTED, Order.CANCELLED])
            .select_related('user', 'slot', 'payment')
            .prefetch_related('lines__item')
            .order_by('slot__start_time', 'created_at'))


def _queue_context():
    orders = list(kitchen_orders())
    return {'orders': orders, 'new_count': sum(1 for o in orders if o.status == Order.PLACED)}


@role_required('is_kitchen')
def queue(request):
    """The live order queue, sorted by pickup time."""
    return render(request, 'kitchen/queue.html', _queue_context())


@role_required('is_kitchen')
def queue_partial(request):
    """Only the queue block, fetched every few seconds by the page."""
    return render(request, 'kitchen/_queue.html', _queue_context())


@role_required('is_kitchen')
@require_POST
def order_action(request, pk):
    """Accept, prepare, mark ready or mark collected."""
    order = get_object_or_404(Order, pk=pk)
    new_status = ACTIONS.get(request.POST.get('action'))
    if new_status is None:
        messages.error(request, 'Unknown action.')
        return redirect('queue')
    try:
        services.change_status(order, new_status)
    except OrderError as exc:
        messages.error(request, str(exc))
    return redirect('queue')


@role_required('is_kitchen')
@require_POST
def order_cancel(request, pk):
    """Cancel an order. A reason is required so the student knows why."""
    order = get_object_or_404(Order, pk=pk)
    reason = request.POST.get('reason', '').strip()
    if not reason:
        messages.error(request, 'Write a short reason before cancelling.')
        return redirect('queue')
    try:
        services.cancel_order(order, reason)
        messages.success(request, f'Order #{order.pk} was cancelled and the student was told.')
    except OrderError as exc:
        messages.error(request, str(exc))
    return redirect('queue')


@login_required
def notifications(request):
    """Show the user's notifications and mark them as read."""
    items = list(Notification.objects.filter(user=request.user)[:50])
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return render(request, 'kitchen/notifications.html', {'items': items})
