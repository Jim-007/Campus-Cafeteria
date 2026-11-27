"""Student screens: cart, checkout, payment, order history and tracking (FR4 to FR7, FR11)."""
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from menu.models import MenuItem
from . import cart, services
from .models import Order, Payment
from .services import OrderError
from .slots import ensure_slots


def _int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


@role_required('is_student')
def cart_view(request):
    """Show the cart with quantity controls."""
    lines, total = cart.lines(request.session)
    return render(request, 'orders/cart.html', {'lines': lines, 'total': total})


@role_required('is_student')
@require_POST
def cart_add(request, item_id):
    """Add one piece of an item to the cart."""
    item = get_object_or_404(MenuItem, pk=item_id)
    if not item.can_order:
        messages.error(request, f'{item.name} is sold out.')
    else:
        cart.add(request.session, item.pk)
        messages.success(request, f'{item.name} added to your cart.')
    target = request.POST.get('next', '')
    if url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}):
        return redirect(target)
    return redirect('menu_list')


@role_required('is_student')
@require_POST
def cart_update(request, item_id):
    """Change the quantity of a cart line. Zero removes it."""
    cart.set_quantity(request.session, item_id, _int(request.POST.get('quantity')))
    return redirect('cart')


@role_required('is_student')
def checkout(request):
    """Choose a pickup slot and payment method, add notes, and place the order."""
    lines, total = cart.lines(request.session)
    if not lines:
        messages.error(request, 'Your cart is empty. Add something from the menu first.')
        return redirect('menu_list')
    slots = ensure_slots()
    if request.method == 'POST':
        slot = next((s for s in slots if s.pk == _int(request.POST.get('slot'))), None)
        if slot is None:
            messages.error(request, 'Choose a pickup time.')
        else:
            try:
                order = services.place_order(
                    request.user, lines, slot, request.POST.get('method', ''),
                    request.POST.get('instructions', '').strip())
            except OrderError as exc:
                messages.error(request, str(exc))
            else:
                cart.clear(request.session)
                if order.payment.status == Payment.PROCESSING:
                    return redirect('pay', pk=order.pk)
                messages.success(request, f'Order #{order.pk} placed. Pay at the counter when you collect.')
                return redirect('order_detail', pk=order.pk)
    return render(request, 'orders/checkout.html', {
        'lines': lines, 'total': total, 'slots': slots, 'methods': Payment.METHODS,
        'chosen_slot': _int(request.POST.get('slot')), 'chosen_method': request.POST.get('method', ''),
        'instructions': request.POST.get('instructions', ''),
    })


@role_required('is_student')
def pay(request, pk):
    """Simulated online payment page. Pay succeeds, Fail cancels the order."""
    order = get_object_or_404(Order, pk=pk, user=request.user)
    if order.payment.status != Payment.PROCESSING:
        return redirect('order_detail', pk=order.pk)
    if request.method == 'POST':
        success = request.POST.get('action') == 'pay'
        services.pay_order(order, success)
        if success:
            messages.success(request, f'Payment received. Order #{order.pk} is placed.')
        else:
            messages.error(request, 'Payment failed. The order was cancelled and you were not charged.')
        return redirect('order_detail', pk=order.pk)
    return render(request, 'orders/pay.html', {'order': order})


@role_required('is_student')
def order_list(request):
    """List the student's own orders (FR6)."""
    orders = Order.objects.filter(user=request.user).select_related('slot', 'payment')
    return render(request, 'orders/order_list.html', {'orders': orders})


@role_required('is_student')
def order_detail(request, pk):
    """Show one order with live status (FR6, FR11)."""
    order = get_object_or_404(Order, pk=pk, user=request.user)
    return render(request, 'orders/order_detail.html', {'order': order})


@role_required('is_student')
def order_status(request, pk):
    """Return only the status block, so the page can refresh it."""
    order = get_object_or_404(Order, pk=pk, user=request.user)
    return render(request, 'orders/_status.html', {'order': order})


@role_required('is_student')
@require_POST
def order_cancel(request, pk):
    """A student may cancel only while staff have not accepted the order."""
    order = get_object_or_404(Order, pk=pk, user=request.user)
    if order.status != Order.PLACED:
        messages.error(request, 'Staff already started this order, so it cannot be cancelled here.')
    else:
        services.cancel_order(order, 'Cancelled by the student')
        messages.success(request, f'Order #{order.pk} was cancelled.')
    return redirect('order_detail', pk=order.pk)


@role_required('is_student')
@require_POST
def order_collect(request, pk):
    """Confirm that the food was collected (UC10)."""
    order = get_object_or_404(Order, pk=pk, user=request.user)
    try:
        services.change_status(order, Order.COLLECTED)
        messages.success(request, 'Thanks! The order is marked as collected.')
    except OrderError as exc:
        messages.error(request, str(exc))
    return redirect('order_detail', pk=order.pk)


@role_required('is_student')
@require_POST
def reorder(request, pk):
    """Fill the cart again with the items of a past order (FR6)."""
    order = get_object_or_404(Order, pk=pk, user=request.user)
    skipped = []
    for line in order.lines.select_related('item'):
        if line.item.can_order:
            cart.set_quantity(request.session, line.item.pk, line.quantity)
        else:
            skipped.append(line.item.name)
    if skipped:
        messages.error(request, 'Sold out and skipped: ' + ', '.join(skipped) + '.')
    return redirect('cart')
