"""Add sample menu items so every member can test with the same data."""
from django.core.management.base import BaseCommand

from menu.models import MenuItem

SAMPLE = [
    ('Chicken Biryani', 'Lunch plate with salad', 180, 'lunch', 'Halal, Spicy', 40),
    ('Beef Tehari', 'Rice with spiced beef', 170, 'lunch', 'Halal, Spicy', 30),
    ('Vegetable Khichuri', 'Rice and lentils with vegetables', 120, 'lunch', 'Halal, Vegetarian', 25),
    ('Paratha and Egg', 'Two parathas with a fried egg', 60, 'breakfast', 'Halal', 50),
    ('Samosa', 'Two pieces', 30, 'snacks', 'Halal, Vegetarian', 80),
    ('Chicken Sandwich', 'Grilled with lettuce', 90, 'snacks', 'Halal', 35),
    ('Masala Tea', 'Hot milk tea', 25, 'beverages', 'Halal, Vegetarian', 100),
    ('Cold Coffee', 'Iced, with milk', 80, 'beverages', 'Vegetarian', 0),
]


class Command(BaseCommand):
    """Create the sample items. Safe to run more than once."""

    help = 'Add sample menu items'

    def handle(self, *args, **options):
        created = 0
        for name, desc, price, cat, tags, stock in SAMPLE:
            _, was_new = MenuItem.objects.get_or_create(
                name=name,
                defaults=dict(description=desc, price=price, category=cat,
                              dietary_tags=tags, stock=stock, is_available=stock > 0),
            )
            created += was_new
        self.stdout.write(self.style.SUCCESS(f'{created} new menu items added.'))
