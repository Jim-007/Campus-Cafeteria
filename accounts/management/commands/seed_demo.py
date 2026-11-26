"""Create demo accounts and menu items so the system can be shown straight away."""
from django.core.management import call_command
from django.core.management.base import BaseCommand

from accounts.models import User

PASSWORD = 'Demo@12345'
DEMO = [
    ('demo_student', 'student@campus.edu', User.STUDENT, 'Demo', 'Student', '2210001'),
    ('demo_staff', 'staff@campus.edu', User.STAFF, 'Demo', 'Staff', ''),
    ('demo_owner', 'owner@campus.edu', User.MANAGER, 'Demo', 'Owner', ''),
]


class Command(BaseCommand):
    """Create one student, one staff and one owner account plus sample food."""

    help = 'Create demo users (password Demo@12345) and sample menu items'

    def handle(self, *args, **options):
        call_command('seed_menu', stdout=self.stdout)
        for username, email, role, first, last, sid in DEMO:
            user, created = User.objects.get_or_create(
                username=username,
                defaults=dict(email=email, role=role, first_name=first, last_name=last, student_id=sid))
            if created:
                user.set_password(PASSWORD)
                user.save()
        self.stdout.write(self.style.SUCCESS(f'Demo users ready. Password for all: {PASSWORD}'))
