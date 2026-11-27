"""Tests for slots, services and the student ordering flow (FR4 to FR7, FR11)."""
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from kitchen.models import Notification
from menu.models import MenuItem
from . import cart, services
from .models import Order, OrderItem, Payment, TimeSlot
from .services import OrderError
from .slots import ensure_slots

PW = 'Str0ng!Pass99'


def make_slot(minutes=30, max_orders=2):
    """A slot that starts in the future."""
    start = timezone.now() + timedelta(minutes=minutes)
    return TimeSlot.objects.create(start_time=start, end_time=start + timedelta(minutes=30), max_orders=max_orders)


class Base(TestCase):
    """Shared users and items."""

    def setUp(self):
        self.student = User.objects.create_user('stu', 'stu@campus.edu', PW)
        self.staff = User.objects.create_user('sam', 'sam@campus.edu', PW, role=User.STAFF)
        self.item = MenuItem.objects.create(name='Samosa', price=Decimal('30'), category='snacks', stock=5)
        self.slot = make_slot()

    def lines(self, qty=2):
        return [{'item': self.item, 'quantity': qty, 'line_total': self.item.price * qty}]

    def place(self, method='counter', qty=2, slot=None):
        return services.place_order(self.student, self.lines(qty), slot or self.slot, method, 'no nuts')


class SlotTests(TestCase):
    """FR5: slot creation and capacity."""

    def test_ensure_slots_makes_future_slots_once(self):
        """Calling twice does not duplicate slots, and all are in the future."""
        first = ensure_slots()
        second = ensure_slots()
        self.assertEqual(len(first), len(second))
        self.assertEqual(TimeSlot.objects.count(), len(first))
        self.assertTrue(all(s.start_time > timezone.now() for s in first))

    def test_slot_full_at_limit_and_cancelled_frees_it(self):
        """Boundary: full at the limit; cancelled orders do not count."""
        user = User.objects.create_user('u', 'u@campus.edu', PW)
        slot = make_slot(max_orders=1)
        o = Order.objects.create(user=user, slot=slot)
        self.assertTrue(slot.is_full)
        o.status = Order.CANCELLED
        o.save()
        self.assertFalse(slot.is_full)
        self.assertEqual(slot.remaining, 1)


class ServiceTests(Base):
    """Business rules."""

    def test_place_counter_order_lowers_stock_and_alerts_staff(self):
        """Stock goes down, payment is pending and staff are notified."""
        order = self.place()
        self.item.refresh_from_db()
        self.assertEqual(self.item.stock, 3)
        self.assertEqual(order.payment.status, Payment.PENDING)
        self.assertEqual(order.total, Decimal('60'))
        self.assertTrue(Notification.objects.filter(user=self.staff, order=order).exists())

    def test_online_order_waits_for_payment_before_staff_see_it(self):
        """Online orders are processing and give staff no alert yet."""
        order = self.place(method='bkash')
        self.assertEqual(order.payment.status, Payment.PROCESSING)
        self.assertFalse(Notification.objects.filter(user=self.staff).exists())
        services.pay_order(order, True)
        order.payment.refresh_from_db()
        self.assertEqual(order.payment.status, Payment.PAID)
        self.assertTrue(order.payment.transaction_ref.startswith('SIM-'))
        self.assertTrue(Notification.objects.filter(user=self.staff, order=order).exists())

    def test_failed_payment_cancels_order_and_returns_stock(self):
        """A failed online payment cancels the order and restores stock."""
        order = self.place(method='card')
        services.pay_order(order, False)
        order.refresh_from_db()
        self.item.refresh_from_db()
        self.assertEqual(order.status, Order.CANCELLED)
        self.assertEqual(order.payment.status, Payment.FAILED)
        self.assertEqual(self.item.stock, 5)

    def test_cannot_order_more_than_stock(self):
        """Boundary: asking for one more than the stock is refused and nothing is saved."""
        with self.assertRaises(OrderError):
            self.place(qty=6)
        self.assertEqual(Order.objects.count(), 0)
        self.item.refresh_from_db()
        self.assertEqual(self.item.stock, 5)

    def test_exact_stock_is_allowed(self):
        """Boundary: ordering exactly the stock works and leaves zero."""
        self.place(qty=5)
        self.item.refresh_from_db()
        self.assertEqual(self.item.stock, 0)

    def test_sold_out_item_is_refused(self):
        """A hidden item cannot be ordered."""
        self.item.is_available = False
        self.item.save()
        with self.assertRaises(OrderError):
            self.place()

    def test_empty_cart_unknown_method_past_and_full_slot(self):
        """Invalid inputs raise clear errors."""
        with self.assertRaises(OrderError):
            services.place_order(self.student, [], self.slot, 'counter')
        with self.assertRaises(OrderError):
            self.place(method='bitcoin')
        old = TimeSlot.objects.create(start_time=timezone.now() - timedelta(minutes=5),
                                      end_time=timezone.now() + timedelta(minutes=25))
        with self.assertRaises(OrderError):
            self.place(slot=old)
        full = make_slot(minutes=90, max_orders=1)
        self.place(qty=1, slot=full)
        with self.assertRaises(OrderError):
            self.place(qty=1, slot=full)

    def test_status_must_follow_the_order(self):
        """Skipping steps or leaving a finished state is refused."""
        order = self.place()
        with self.assertRaises(OrderError):
            services.change_status(order, Order.READY)
        for status in (Order.ACCEPTED, Order.PREPARING, Order.READY, Order.COLLECTED):
            services.change_status(order, status)
        with self.assertRaises(OrderError):
            services.change_status(order, Order.PREPARING)
        order.payment.refresh_from_db()
        self.assertEqual(order.payment.status, Payment.PAID)  # cash taken at handover

    def test_student_is_notified_on_each_change(self):
        """Every status change creates a message for the student."""
        order = self.place()
        services.change_status(order, Order.ACCEPTED)
        services.change_status(order, Order.PREPARING)
        self.assertEqual(Notification.objects.filter(user=self.student, order=order).count(), 2)

    def test_cancel_refunds_paid_order_and_restores_stock(self):
        """A paid order that is cancelled is refunded and the stock returns."""
        order = self.place(method='nagad')
        services.pay_order(order, True)
        services.cancel_order(order, 'Item burnt')
        order.refresh_from_db()
        self.item.refresh_from_db()
        self.assertEqual(order.payment.status, Payment.REFUNDED)
        self.assertEqual(order.cancel_reason, 'Item burnt')
        self.assertEqual(self.item.stock, 5)
        with self.assertRaises(OrderError):
            services.cancel_order(order, 'again')


class StudentFlowTests(Base):
    """The student screens end to end."""

    def setUp(self):
        super().setUp()
        self.client.force_login(self.student)

    def test_cart_add_update_and_limit(self):
        """Adding, updating and removing change the cart."""
        self.client.post(reverse('cart_add', args=[self.item.pk]))
        self.client.post(reverse('cart_add', args=[self.item.pk]))
        self.assertEqual(cart.count(self.client.session), 2)
        self.client.post(reverse('cart_update', args=[self.item.pk]), {'quantity': '99'})
        self.assertEqual(cart.count(self.client.session), cart.MAX_PER_ITEM)
        self.client.post(reverse('cart_update', args=[self.item.pk]), {'quantity': '0'})
        self.assertEqual(cart.count(self.client.session), 0)

    def test_cannot_add_sold_out_item(self):
        """A sold out item is not added."""
        self.item.stock = 0
        self.item.save()
        self.client.post(reverse('cart_add', args=[self.item.pk]))
        self.assertEqual(cart.count(self.client.session), 0)

    def test_empty_cart_checkout_redirects(self):
        """Checkout with nothing in the cart goes back to the menu."""
        self.assertRedirects(self.client.get(reverse('checkout')), reverse('menu_list'))

    def test_counter_checkout_creates_order(self):
        """Full flow: add, checkout with counter payment, see the order."""
        self.client.post(reverse('cart_add', args=[self.item.pk]))
        slot = ensure_slots()[0]
        resp = self.client.post(reverse('checkout'), {'slot': slot.pk, 'method': 'counter', 'instructions': 'less oil'})
        order = Order.objects.get()
        self.assertRedirects(resp, reverse('order_detail', args=[order.pk]))
        self.assertEqual(cart.count(self.client.session), 0)
        self.assertContains(self.client.get(reverse('order_detail', args=[order.pk])), 'Placed')

    def test_online_checkout_goes_to_payment_and_pays(self):
        """Online method goes to the payment page; Pay now marks it paid."""
        self.client.post(reverse('cart_add', args=[self.item.pk]))
        slot = ensure_slots()[0]
        resp = self.client.post(reverse('checkout'), {'slot': slot.pk, 'method': 'bkash'})
        order = Order.objects.get()
        self.assertRedirects(resp, reverse('pay', args=[order.pk]))
        self.client.post(reverse('pay', args=[order.pk]), {'action': 'pay'})
        order.payment.refresh_from_db()
        self.assertEqual(order.payment.status, Payment.PAID)

    def test_checkout_without_slot_or_method_shows_error(self):
        """Missing choices keep the student on the checkout page."""
        self.client.post(reverse('cart_add', args=[self.item.pk]))
        resp = self.client.post(reverse('checkout'), {'method': 'counter'})
        self.assertContains(resp, 'Choose a pickup time')
        slot = ensure_slots()[0]
        resp = self.client.post(reverse('checkout'), {'slot': slot.pk})
        self.assertContains(resp, 'Choose a payment method')
        self.assertEqual(Order.objects.count(), 0)

    def test_student_cancel_only_before_acceptance(self):
        """Cancel works while Placed and is refused once accepted."""
        order = self.place()
        self.client.post(reverse('order_cancel', args=[order.pk]))
        order.refresh_from_db()
        self.assertEqual(order.status, Order.CANCELLED)
        second = self.place()
        services.change_status(second, Order.ACCEPTED)
        self.client.post(reverse('order_cancel', args=[second.pk]))
        second.refresh_from_db()
        self.assertEqual(second.status, Order.ACCEPTED)

    def test_confirm_pickup_only_when_ready(self):
        """Collected can be confirmed only from Ready."""
        order = self.place()
        self.client.post(reverse('order_collect', args=[order.pk]))
        order.refresh_from_db()
        self.assertEqual(order.status, Order.PLACED)
        for status in (Order.ACCEPTED, Order.PREPARING, Order.READY):
            services.change_status(order, status)
        self.client.post(reverse('order_collect', args=[order.pk]))
        order.refresh_from_db()
        self.assertEqual(order.status, Order.COLLECTED)

    def test_students_only_see_their_own_orders(self):
        """Another student's order returns 404 and is not listed."""
        other = User.objects.create_user('other', 'other@campus.edu', PW)
        theirs = Order.objects.create(user=other, slot=self.slot)
        Payment.objects.create(order=theirs, method='counter', amount=0)
        self.assertEqual(self.client.get(reverse('order_detail', args=[theirs.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse('order_status', args=[theirs.pk])).status_code, 404)
        self.assertNotContains(self.client.get(reverse('order_list')), f'#{theirs.pk}')

    def test_reorder_fills_cart_and_skips_sold_out(self):
        """Reorder copies items that can still be ordered."""
        order = self.place(qty=2)
        self.client.post(reverse('reorder', args=[order.pk]))
        self.assertEqual(cart.count(self.client.session), 2)
        self.client.post(reverse('cart_update', args=[self.item.pk]), {'quantity': '0'})
        self.item.is_available = False
        self.item.save()
        self.client.post(reverse('reorder', args=[order.pk]))
        self.assertEqual(cart.count(self.client.session), 0)

    def test_status_partial_and_tracking_steps(self):
        """The refresh block shows the step bar."""
        order = self.place()
        services.change_status(order, Order.ACCEPTED)
        resp = self.client.get(reverse('order_status', args=[order.pk]))
        self.assertContains(resp, 'Accepted')
        order.refresh_from_db()
        self.assertEqual([s['state'] for s in order.progress][:2], ['done', 'current'])
