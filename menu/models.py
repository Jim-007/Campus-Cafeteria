"""Menu item model (FR3, FR8)."""
from django.db import models


class MenuItem(models.Model):
    """A food or drink item the cafeteria sells."""

    CATEGORIES = [
        ('breakfast', 'Breakfast'),
        ('lunch', 'Lunch'),
        ('snacks', 'Snacks'),
        ('beverages', 'Beverages'),
    ]

    name = models.CharField(max_length=100)
    description = models.CharField(max_length=200, blank=True)
    price = models.DecimalField(max_digits=7, decimal_places=2)
    category = models.CharField(max_length=20, choices=CATEGORIES)
    dietary_tags = models.CharField(
        max_length=100, blank=True,
        help_text='Comma separated, for example: Halal, Vegetarian',
    )
    stock = models.PositiveIntegerField(default=0)
    is_available = models.BooleanField(default=True)

    class Meta:
        ordering = ['category', 'name']

    def __str__(self):
        return self.name

    @property
    def tag_list(self):
        """Return the dietary tags as a clean list."""
        return [t.strip() for t in self.dietary_tags.split(',') if t.strip()]

    @property
    def can_order(self):
        """An item can be ordered only when it is available and in stock."""
        return self.is_available and self.stock > 0
