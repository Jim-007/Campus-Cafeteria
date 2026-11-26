"""Template context shared by every page: unread notifications and cart size."""
from kitchen.models import Notification
from orders import cart


def nav_counts(request):
    """Return the numbers shown in the navigation bar."""
    user = request.user
    if not user.is_authenticated:
        return {}
    data = {'unread_count': Notification.objects.filter(user=user, is_read=False).count()}
    if user.is_student:
        data['cart_count'] = cart.count(request.session)
    return data
