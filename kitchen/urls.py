"""URLs for the kitchen queue and notifications."""
from django.urls import path

from . import views

urlpatterns = [
    path('queue/', views.queue, name='queue'),
    path('queue/partial/', views.queue_partial, name='queue_partial'),
    path('order/<int:pk>/action/', views.order_action, name='order_action'),
    path('order/<int:pk>/cancel/', views.order_cancel, name='kitchen_cancel'),
    path('notifications/', views.notifications, name='notifications'),
]
