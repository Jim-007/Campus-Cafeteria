"""Session based shopping cart (FR4). The cart is a dict of item id to quantity."""
from decimal import Decimal

from menu.models import MenuItem

KEY = 'cart'
MAX_PER_ITEM = 10


def _get(session):
    return dict(session.get(KEY, {}))


def _save(session, cart):
    session[KEY] = cart
    session.modified = True


def add(session, item_id, quantity=1):
    """Add quantity of an item, never above the per-item limit."""
    cart = _get(session)
    key = str(item_id)
    cart[key] = min(cart.get(key, 0) + quantity, MAX_PER_ITEM)
    _save(session, cart)


def set_quantity(session, item_id, quantity):
    """Set an exact quantity. Zero or less removes the item."""
    cart = _get(session)
    key = str(item_id)
    if quantity <= 0:
        cart.pop(key, None)
    else:
        cart[key] = min(quantity, MAX_PER_ITEM)
    _save(session, cart)


def clear(session):
    """Empty the cart."""
    _save(session, {})


def count(session):
    """Total number of pieces in the cart."""
    return sum(_get(session).values())


def lines(session):
    """Return (lines, total). Each line is a dict with item, quantity and line_total."""
    cart = _get(session)
    items = MenuItem.objects.in_bulk([int(k) for k in cart])
    result, total = [], Decimal('0')
    for key, qty in cart.items():
        item = items.get(int(key))
        if item is None:
            continue
        line_total = item.price * qty
        total += line_total
        result.append({'item': item, 'quantity': qty, 'line_total': line_total})
    return result, total
