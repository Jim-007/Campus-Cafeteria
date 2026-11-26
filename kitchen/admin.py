"""Admin registration for notifications."""
from django.contrib import admin

from .models import Notification

admin.site.register(Notification)
