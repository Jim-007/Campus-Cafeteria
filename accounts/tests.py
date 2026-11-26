"""Tests for registration, login and role based access (FR1, FR2)."""
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import User

VALID = {
    'first_name': 'Rafi', 'last_name': 'Ahmed', 'username': 'rafi',
    'student_id': '2210001', 'email': 'rafi@campus.edu', 'role': 'student',
    'access_code': '', 'password1': 'Str0ng!Pass99', 'password2': 'Str0ng!Pass99',
}
PW = 'Str0ng!Pass99'


class RegisterTests(TestCase):
    """FR1: registration, normal, invalid and duplicate cases."""

    def test_student_registration(self):
        """A student can register without a code."""
        resp = self.client.post(reverse('register'), VALID)
        self.assertRedirects(resp, reverse('login'))
        self.assertEqual(User.objects.get(username='rafi').role, User.STUDENT)

    @override_settings(STAFF_ACCESS_CODE='SECRET')
    def test_staff_needs_the_access_code(self):
        """Choosing staff with a wrong code must fail."""
        resp = self.client.post(reverse('register'), dict(VALID, role='staff', access_code='nope'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'access code is wrong')
        self.assertEqual(User.objects.count(), 0)

    @override_settings(STAFF_ACCESS_CODE='SECRET')
    def test_staff_and_owner_register_with_the_code(self):
        """The right code creates staff and owner accounts."""
        self.client.post(reverse('register'), dict(VALID, role='staff', access_code='SECRET'))
        self.client.post(reverse('register'), dict(VALID, username='boss', email='boss@campus.edu',
                                                   role='manager', access_code='SECRET'))
        self.assertEqual(User.objects.get(username='rafi').role, User.STAFF)
        self.assertEqual(User.objects.get(username='boss').role, User.MANAGER)

    def test_cannot_register_as_admin(self):
        """The admin role is not offered on the form."""
        resp = self.client.post(reverse('register'), dict(VALID, role='admin'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(User.objects.count(), 0)

    def test_duplicate_email_is_rejected(self):
        """The same email cannot register twice, even with different letter case."""
        self.client.post(reverse('register'), VALID)
        resp = self.client.post(reverse('register'), dict(VALID, username='rafi2', email='RAFI@campus.edu'))
        self.assertContains(resp, 'already registered')
        self.assertEqual(User.objects.count(), 1)

    def test_password_mismatch_and_weak_password(self):
        """Mismatched or weak passwords create no account."""
        self.client.post(reverse('register'), dict(VALID, password2='different'))
        self.client.post(reverse('register'), dict(VALID, password1='12345', password2='12345'))
        self.assertEqual(User.objects.count(), 0)

    def test_superuser_becomes_admin_role(self):
        """createsuperuser accounts always get the admin role."""
        admin = User.objects.create_superuser('root', 'root@campus.edu', PW)
        self.assertEqual(admin.role, User.ADMIN)
        self.assertTrue(admin.is_owner)


class LoginAndAccessTests(TestCase):
    """FR2: login, logout and where each role lands."""

    @classmethod
    def setUpTestData(cls):
        cls.student = User.objects.create_user('sara', 'sara@campus.edu', PW)
        cls.staff = User.objects.create_user('sam', 'sam@campus.edu', PW, role=User.STAFF)
        cls.owner = User.objects.create_user('olu', 'olu@campus.edu', PW, role=User.MANAGER)

    def _login(self, name):
        return self.client.post(reverse('login'), {'username': name, 'password': PW}, follow=False)

    def test_each_role_lands_on_its_own_page(self):
        """Student sees the menu, staff the queue, owner the reports."""
        for name, target in [('sara', 'menu_list'), ('sam', 'queue'), ('olu', 'reports')]:
            self.client.logout()
            self._login(name)
            resp = self.client.get(reverse('home'))
            self.assertRedirects(resp, reverse(target))

    def test_wrong_password_keeps_user_out(self):
        """Wrong credentials show an error and no session starts."""
        resp = self.client.post(reverse('login'), {'username': 'sara', 'password': 'bad'})
        self.assertContains(resp, 'wrong')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_logout_ends_session(self):
        """Signing out removes the session."""
        self.client.force_login(self.student)
        self.client.post(reverse('logout'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_anonymous_visitor_is_sent_to_login(self):
        """Protected pages redirect to sign in."""
        for name in ['menu_list', 'cart', 'queue', 'reports', 'manage_menu']:
            resp = self.client.get(reverse(name))
            self.assertEqual(resp.status_code, 302)
            self.assertIn(reverse('login'), resp['Location'])

    def test_student_cannot_open_staff_or_owner_pages(self):
        """A student is turned away from the queue, reports and menu management."""
        self.client.force_login(self.student)
        for name in ['queue', 'reports', 'manage_menu', 'item_create']:
            self.assertRedirects(self.client.get(reverse(name)), reverse('home'), fetch_redirect_response=False)

    def test_staff_cannot_open_owner_pages_or_the_cart(self):
        """Staff may not manage the menu, see reports or use the cart."""
        self.client.force_login(self.staff)
        for name in ['reports', 'manage_menu', 'cart', 'order_list']:
            self.assertRedirects(self.client.get(reverse(name)), reverse('home'), fetch_redirect_response=False)
