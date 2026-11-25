"""URLs for the menu, menu management and reports."""
from django.urls import path

from . import reports, views

urlpatterns = [
    path('', views.menu_list, name='menu_list'),
    path('manage/', views.manage_list, name='manage_menu'),
    path('manage/new/', views.item_create, name='item_create'),
    path('manage/<int:pk>/edit/', views.item_edit, name='item_edit'),
    path('manage/<int:pk>/toggle/', views.item_toggle, name='item_toggle'),
    path('manage/<int:pk>/delete/', views.item_delete, name='item_delete'),
    path('reports/', reports.report, name='reports'),
]
