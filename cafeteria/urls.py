"""Root URL configuration for the Campus Cafeteria project."""
from django.contrib import admin
from django.urls import path, include

from accounts.views import home

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    path('accounts/', include('accounts.urls')),
    path('menu/', include('menu.urls')),
    path('orders/', include('orders.urls')),
    path('kitchen/', include('kitchen.urls')),
]
