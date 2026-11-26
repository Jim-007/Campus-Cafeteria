"""Registration (FR1) and the role-based home redirect (FR2)."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import RegisterForm


def register(request):
    """Show the registration form and create the account on submit."""
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Account created. You can sign in now.')
            return redirect('login')
    else:
        form = RegisterForm()
    return render(request, 'accounts/register.html', {'form': form})


@login_required
def home(request):
    """Send each role to its own starting page after sign in."""
    user = request.user
    if user.is_owner:
        return redirect('reports')
    if user.is_kitchen:
        return redirect('queue')
    return redirect('menu_list')
