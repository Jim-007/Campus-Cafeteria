"""Admin registration for users."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CafeteriaUserAdmin(UserAdmin):
    """Show the role and student ID in the admin user screens."""

    fieldsets = UserAdmin.fieldsets + (('Cafeteria', {'fields': ('role', 'student_id')}),)
    list_display = ('username', 'email', 'role', 'is_active')
    list_filter = ('role', 'is_active')
