"""Tests for the staff queue and notifications (FR9, FR10, FR11)."""
from datetime import timedelta
from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from menu.models import MenuItem
from orders import services
from orders.models import Order, Payment, TimeSlot
from .models import Notification

PW = 'Str0ng!Pass99'


class KitchenTests(TestCase):
    """Queue visibility, actions and alerts."""

    def setUp(self):
        self.student = User.objects.create_user('stu', 'stu@campus.edu', PW)
        self.staff = User.objects.create_user('sam', 'sam@campus.edu', PW, role=User.STAFF)
        self.item = MenuItem.objects.create(name='Samosa', price=Decimal('30'), category='snacks', stock=9)
        start = timezone.now() + timedelta(minutes=30)
        self.slot = TimeSlot.objects.create(start_time=start, end_time=start + timedelta(minutes=30))
        self.client.force_login(self.staff)

    def place(self, method='counter'):
        lines = [{'item': self.item, 'quantity': 1, 'line_total': self.item.price}]
        return services.place_order(self.student, lines, self.slot, method)

    def test_queue_shows_counter_orders_but_hides_unpaid_online_orders(self):
        """An online order appears only after it is paid."""
        counter = self.place()
        online = self.place('bkash')
        resp = self.client.get(reverse('queue'))
        self.assertContains(resp, f'Order #{counter.pk}')
        self.assertNotContains(resp, f'Order #{online.pk} ')
        services.pay_order(online, True)
        self.assertContains(self.client.get(reverse('queue_partial')), f'Order #{online.pk}')

    def test_new_order_banner_counts_placed_orders(self):
        """The partial reports how many orders wait for acceptance."""
        self.place()
        self.place()
        self.assertContains(self.client.get(reverse('queue_partial')), 'data-new-count="2"')

    def test_staff_moves_order_through_all_steps(self):
        """Accept, prepare, ready and handed over update the status."""
        order = self.place()
        for action, expected in [('accept', Order.ACCEPTED), ('prepare', Order.PREPARING),
                                 ('ready', Order.READY), ('collect', Order.COLLECTED)]:
            self.client.post(reverse('order_action', args=[order.pk]), {'action': action})
            order.refresh_from_db()
            self.assertEqual(order.status, expected)
        self.assertNotContains(self.client.get(reverse('queue_partial')), f'Order #{order.pk}')

    def test_invalid_action_and_skipped_step_change_nothing(self):
        """Unknown actions and skipping a step are refused."""
        order = self.place()
        self.client.post(reverse('order_action', args=[order.pk]), {'action': 'fly'})
        self.client.post(reverse('order_action', args=[order.pk]), {'action': 'ready'})
        order.refresh_from_db()
        self.assertEqual(order.status, Order.PLACED)

    def test_cancel_needs_a_reason_and_tells_the_student(self):
        """Empty reason is refused; a reason cancels, restores stock and notifies."""
        order = self.place()
        self.client.post(reverse('kitchen_cancel', args=[order.pk]), {'reason': '  '})
        order.refresh_from_db()
        self.assertEqual(order.status, Order.PLACED)
        self.client.post(reverse('kitchen_cancel', args=[order.pk]), {'reason': 'Ran out'})
        order.refresh_from_db()
        self.item.refresh_from_db()
        self.assertEqual(order.status, Order.CANCELLED)
        self.assertEqual(self.item.stock, 9)
        self.assertTrue(Notification.objects.filter(user=self.student, message__contains='Ran out').exists())

    def test_actions_need_post(self):
        """GET on an action URL is not allowed."""
        order = self.place()
        self.assertEqual(self.client.get(reverse('order_action', args=[order.pk])).status_code, 405)

    def test_notifications_page_marks_read(self):
        """Opening alerts shows the message and clears the unread count."""
        self.place()
        self.assertEqual(Notification.objects.filter(user=self.staff, is_read=False).count(), 1)
        self.assertContains(self.client.get(reverse('notifications')), 'New order')
        self.assertEqual(Notification.objects.filter(user=self.staff, is_read=False).count(), 0)

    def test_unread_count_shows_in_navigation(self):
        """The bar shows the number of unread alerts."""
        self.place()
        self.assertContains(self.client.get(reverse('queue')), 'badge-count')

    def test_no_show_command_cancels_late_orders(self):
        """Orders not collected long after their slot are cancelled."""
        order = self.place()
        self.slot.start_time = timezone.now() - timedelta(minutes=30)
        self.slot.end_time = timezone.now()
        self.slot.save()
        call_command('cancel_no_shows', stdout=StringIO())
        order.refresh_from_db()
        self.assertEqual(order.status, Order.CANCELLED)
        self.assertIn('No-show', order.cancel_reason)
