"""Tests for the owner's sales report (FR12)."""
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from orders import services
from orders.models import Order, TimeSlot
from .models import MenuItem

PW = 'Str0ng!Pass99'


class ReportTests(TestCase):
    """Totals, ranges, CSV and access."""

    def setUp(self):
        self.owner = User.objects.create_user('olu', 'olu@campus.edu', PW, role=User.MANAGER)
        self.student = User.objects.create_user('stu', 'stu@campus.edu', PW)
        self.item = MenuItem.objects.create(name='Samosa', price=Decimal('30'), category='snacks', stock=50)
        start = timezone.now() + timedelta(minutes=30)
        self.slot = TimeSlot.objects.create(start_time=start, end_time=start + timedelta(minutes=30), max_orders=20)

    def place(self, qty, method='counter'):
        lines = [{'item': self.item, 'quantity': qty, 'line_total': self.item.price * qty}]
        return services.place_order(self.student, lines, self.slot, method)

    def test_empty_report_renders(self):
        """No sales shows zero and friendly text."""
        self.client.force_login(self.owner)
        resp = self.client.get(reverse('reports'))
        self.assertContains(resp, 'No sales in this period yet')
        self.assertEqual(resp.context['revenue'], 0)

    def test_totals_ignore_cancelled_orders(self):
        """Revenue counts valid orders only."""
        self.place(2)
        cancelled = self.place(5)
        services.cancel_order(cancelled, 'test')
        self.client.force_login(self.owner)
        resp = self.client.get(reverse('reports'))
        self.assertEqual(resp.context['revenue'], Decimal('60'))
        self.assertEqual(resp.context['order_count'], 1)
        self.assertEqual(resp.context['cancelled_count'], 1)
        self.assertEqual(resp.context['top_items'][0]['qty'], 2)

    def test_old_orders_fall_outside_today(self):
        """Orders older than the range are left out."""
        order = self.place(1)
        Order.objects.filter(pk=order.pk).update(created_at=timezone.now() - timedelta(days=3))
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(reverse('reports'), {'days': '1'}).context['order_count'], 0)
        self.assertEqual(self.client.get(reverse('reports'), {'days': '7'}).context['order_count'], 1)

    def test_bad_range_falls_back_to_today(self):
        """An unknown range value does not break the page."""
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(reverse('reports'), {'days': 'abc'}).status_code, 200)

    def test_csv_export(self):
        """The CSV has a header and one row per order."""
        order = self.place(1)
        self.client.force_login(self.owner)
        resp = self.client.get(reverse('reports'), {'export': 'csv'})
        self.assertEqual(resp['Content-Type'], 'text/csv')
        body = resp.content.decode()
        self.assertIn('Order,Date,Customer', body)
        self.assertIn(f'{order.pk},', body)

    def test_students_cannot_open_reports(self):
        """Only owners see financial data."""
        self.client.force_login(self.student)
        self.assertEqual(self.client.get(reverse('reports')).status_code, 302)
