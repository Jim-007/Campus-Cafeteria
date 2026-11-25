"""Form the owner uses to add and edit menu items (FR8)."""
from django import forms

from .models import MenuItem


class MenuItemForm(forms.ModelForm):
    """Add or edit one menu item."""

    class Meta:
        model = MenuItem
        fields = ['name', 'description', 'price', 'category', 'dietary_tags', 'stock', 'is_available']

    def clean_price(self):
        """Price must be above zero."""
        price = self.cleaned_data['price']
        if price <= 0:
            raise forms.ValidationError('Price must be more than zero.')
        return price
