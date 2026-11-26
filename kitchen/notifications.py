"""Helpers to create notifications."""
from accounts.models import User
from .models import Notification


def notify(user, message, order=None):
    """Send a notification to one user."""
    return Notification.objects.create(user=user, message=message, order=order)


def notify_staff(message, order=None):
    """Send a notification to every active staff member, owner and administrator."""
    users = User.objects.filter(role__in=[User.STAFF, User.MANAGER, User.ADMIN], is_active=True)
    Notification.objects.bulk_create([Notification(user=u, message=message, order=order) for u in users])
