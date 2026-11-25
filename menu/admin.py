"""Admin screens the manager uses to manage the menu (FR8)."""
from django.contrib import admin

from .models import MenuItem


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    """List, search and edit menu items."""

    list_display = ('name', 'category', 'price', 'stock', 'is_available')
    list_filter = ('category', 'is_available')
    search_fields = ('name', 'dietary_tags')
