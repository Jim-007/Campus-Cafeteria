"""Access control by role."""
from functools import wraps

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import redirect


def role_required(attr):
    """Allow a view only when ``request.user.<attr>`` is true (for example ``is_owner``)."""

    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if not getattr(request.user, attr):
                messages.error(request, 'Your account does not have access to that page.')
                return redirect('home')
            return view(request, *args, **kwargs)

        return wrapper

    return decorator
