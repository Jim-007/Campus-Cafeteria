"""Menu page (FR3) and menu management for the owner (FR8)."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from .forms import MenuItemForm
from .models import MenuItem

DIETARY_TAGS = ['Halal', 'Vegetarian', 'Vegan', 'Gluten-Free', 'Spicy']


@login_required
def menu_list(request):
    """Show menu items, filtered by search text, category and dietary tag."""
    items = MenuItem.objects.all()
    query = request.GET.get('q', '').strip()
    category = request.GET.get('category', '')
    tag = request.GET.get('tag', '').strip()

    if query:
        items = items.filter(name__icontains=query)
    if category:
        items = items.filter(category=category)
    if tag:
        items = items.filter(dietary_tags__icontains=tag)

    context = {
        'items': items,
        'categories': MenuItem.CATEGORIES,
        'tags': DIETARY_TAGS,
        'q': query,
        'selected_category': category,
        'selected_tag': tag,
    }
    return render(request, 'menu/menu_list.html', context)


@role_required('is_owner')
def manage_list(request):
    """List every item with edit, delete and availability controls."""
    return render(request, 'menu/manage_list.html', {'items': MenuItem.objects.all()})


@role_required('is_owner')
def item_create(request):
    """Add a new menu item."""
    form = MenuItemForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        item = form.save()
        messages.success(request, f'{item.name} was added to the menu.')
        return redirect('manage_menu')
    return render(request, 'menu/item_form.html', {'form': form, 'title': 'Add menu item'})


@role_required('is_owner')
def item_edit(request, pk):
    """Change an existing menu item."""
    item = get_object_or_404(MenuItem, pk=pk)
    form = MenuItemForm(request.POST or None, instance=item)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'{item.name} was updated.')
        return redirect('manage_menu')
    return render(request, 'menu/item_form.html', {'form': form, 'title': f'Edit {item.name}'})


@role_required('is_owner')
@require_POST
def item_toggle(request, pk):
    """Switch an item between available and sold out."""
    item = get_object_or_404(MenuItem, pk=pk)
    item.is_available = not item.is_available
    item.save(update_fields=['is_available'])
    state = 'available' if item.is_available else 'hidden as sold out'
    messages.success(request, f'{item.name} is now {state}.')
    return redirect('manage_menu')


@role_required('is_owner')
@require_POST
def item_delete(request, pk):
    """Delete an item. If past orders use it, hide it instead."""
    item = get_object_or_404(MenuItem, pk=pk)
    try:
        item.delete()
        messages.success(request, f'{item.name} was deleted.')
    except ProtectedError:
        item.is_available = False
        item.save(update_fields=['is_available'])
        messages.error(request, f'{item.name} is in past orders, so it was hidden instead of deleted.')
    return redirect('manage_menu')
