"""URLs for student ordering."""
from django.urls import path

from . import views

urlpatterns = [
    path('cart/', views.cart_view, name='cart'),
    path('cart/add/<int:item_id>/', views.cart_add, name='cart_add'),
    path('cart/update/<int:item_id>/', views.cart_update, name='cart_update'),
    path('checkout/', views.checkout, name='checkout'),
    path('', views.order_list, name='order_list'),
    path('<int:pk>/', views.order_detail, name='order_detail'),
    path('<int:pk>/status/', views.order_status, name='order_status'),
    path('<int:pk>/pay/', views.pay, name='pay'),
    path('<int:pk>/cancel/', views.order_cancel, name='order_cancel'),
    path('<int:pk>/collect/', views.order_collect, name='order_collect'),
    path('<int:pk>/reorder/', views.reorder, name='reorder'),
]
