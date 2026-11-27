"""Admin screens for orders, slots and payments."""
from django.contrib import admin

from .models import Order, OrderItem, Payment, TimeSlot


class OrderItemInline(admin.TabularInline):
    """Show order lines inside the order screen."""

    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """List and edit orders."""

    list_display = ('id', 'user', 'slot', 'status', 'created_at')
    list_filter = ('status',)
    inlines = [OrderItemInline]


admin.site.register(TimeSlot)
admin.site.register(Payment)
