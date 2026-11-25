"""Tests for the menu page (FR3) and menu management (FR8)."""
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from orders.models import Order, OrderItem, Payment, TimeSlot
from django.utils import timezone
from datetime import timedelta
from .models import MenuItem

PW = 'Str0ng!Pass99'


class MenuItemModelTests(TestCase):
    """Boundary cases for stock and tags."""

    def test_can_order_needs_stock_and_availability(self):
        """Zero stock or a hidden item cannot be ordered; one in stock can."""
        self.assertTrue(MenuItem(name='A', price=10, category='lunch', stock=1).can_order)
        self.assertFalse(MenuItem(name='B', price=10, category='lunch', stock=0).can_order)
        self.assertFalse(MenuItem(name='C', price=10, category='lunch', stock=5, is_available=False).can_order)

    def test_tag_list_cleans_spaces_and_blanks(self):
        """Messy tag text becomes a clean list; empty text gives an empty list."""
        self.assertEqual(MenuItem(dietary_tags=' Halal ,, Vegan ').tag_list, ['Halal', 'Vegan'])
        self.assertEqual(MenuItem(dietary_tags='').tag_list, [])


class MenuViewTests(TestCase):
    """Search and filter behaviour on the menu page."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('amy', 'amy@campus.edu', PW)
        MenuItem.objects.create(name='Chicken Biryani', price=Decimal('180'), category='lunch',
                                dietary_tags='Halal, Spicy', stock=10)
        MenuItem.objects.create(name='Veg Khichuri', price=Decimal('120'), category='lunch',
                                dietary_tags='Halal, Vegetarian', stock=5)
        MenuItem.objects.create(name='Cold Coffee', price=Decimal('80'), category='beverages',
                                dietary_tags='Vegetarian', stock=0, is_available=False)

    def setUp(self):
        self.client.force_login(self.user)

    def test_lists_all_items_and_marks_sold_out(self):
        """Every item is shown and the one without stock is marked."""
        resp = self.client.get(reverse('menu_list'))
        for name in ('Chicken Biryani', 'Veg Khichuri', 'Cold Coffee', 'Sold out'):
            self.assertContains(resp, name)

    def test_student_sees_add_to_cart_only_for_orderable_items(self):
        """Two orderable items give two Add to cart buttons."""
        self.assertContains(self.client.get(reverse('menu_list')), 'Add to cart', count=2)

    def test_search_filters_and_combinations(self):
        """Search, category and tag filters narrow the list."""
        resp = self.client.get(reverse('menu_list'), {'q': 'BIRYANI'})
        self.assertContains(resp, 'Chicken Biryani')
        self.assertNotContains(resp, 'Veg Khichuri')
        resp = self.client.get(reverse('menu_list'), {'category': 'beverages'})
        self.assertNotContains(resp, 'Chicken Biryani')
        resp = self.client.get(reverse('menu_list'), {'category': 'lunch', 'tag': 'Spicy'})
        self.assertContains(resp, 'Chicken Biryani')
        self.assertNotContains(resp, 'Veg Khichuri')

    def test_no_match_message_and_html_escaping(self):
        """No result shows a message; script text is escaped."""
        self.assertContains(self.client.get(reverse('menu_list'), {'q': 'pizza'}), 'No items match your search')
        self.assertNotContains(self.client.get(reverse('menu_list'), {'q': '<script>x</script>'}), '<script>x</script>')


class MenuManagementTests(TestCase):
    """FR8: the owner manages the menu."""

    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user('olu', 'olu@campus.edu', PW, role=User.MANAGER)
        cls.item = MenuItem.objects.create(name='Samosa', price=Decimal('30'), category='snacks', stock=10)
        cls.data = {'name': 'Pizza', 'description': '', 'price': '250', 'category': 'lunch',
                    'dietary_tags': 'Halal', 'stock': '5', 'is_available': 'on'}

    def setUp(self):
        self.client.force_login(self.owner)

    def test_owner_can_add_item(self):
        """A valid form adds the item."""
        self.client.post(reverse('item_create'), self.data)
        self.assertTrue(MenuItem.objects.filter(name='Pizza').exists())

    def test_price_must_be_positive(self):
        """Zero price is refused."""
        resp = self.client.post(reverse('item_create'), dict(self.data, price='0'))
        self.assertContains(resp, 'more than zero')
        self.assertFalse(MenuItem.objects.filter(name='Pizza').exists())

    def test_missing_name_is_refused(self):
        """A required field cannot be left empty."""
        self.client.post(reverse('item_create'), dict(self.data, name=''))
        self.assertEqual(MenuItem.objects.count(), 1)

    def test_owner_can_edit_and_toggle(self):
        """Edit changes the price and toggle hides the item."""
        self.client.post(reverse('item_edit', args=[self.item.pk]), dict(self.data, name='Samosa', price='35'))
        self.item.refresh_from_db()
        self.assertEqual(self.item.price, Decimal('35'))
        self.client.post(reverse('item_toggle', args=[self.item.pk]))
        self.item.refresh_from_db()
        self.assertFalse(self.item.is_available)

    def test_delete_unused_item(self):
        """An item no order uses can be deleted."""
        self.client.post(reverse('item_delete', args=[self.item.pk]))
        self.assertFalse(MenuItem.objects.filter(pk=self.item.pk).exists())

    def test_delete_item_in_past_orders_hides_it(self):
        """An item inside an order is hidden, not deleted."""
        student = User.objects.create_user('stu', 'stu@campus.edu', PW)
        now = timezone.now()
        slot = TimeSlot.objects.create(start_time=now, end_time=now + timedelta(minutes=30))
        order = Order.objects.create(user=student, slot=slot)
        OrderItem.objects.create(order=order, item=self.item, quantity=1, unit_price=30)
        Payment.objects.create(order=order, method='counter', amount=30)
        self.client.post(reverse('item_delete', args=[self.item.pk]))
        self.item.refresh_from_db()
        self.assertFalse(self.item.is_available)
