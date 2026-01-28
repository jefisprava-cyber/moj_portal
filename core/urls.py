from django.contrib import admin
from django.urls import path
from products import views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Hlavná stránka
    path('', views.home, name='home'),
    
    # Produkty a Kategórie
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    
    # Košík a manipulácia
    path('add/<int:offer_id>/', views.add_to_cart, name='add_to_cart'),
    path('remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/', views.cart_detail, name='cart_detail'),
    
    # Killer Feature: Optimalizácia a Checkout
    path('optimize/', views.optimize_cart, name='optimize_cart'),
    path('checkout/', views.checkout, name='checkout'),
    
    # Registrácia
    path('register/', views.register, name='register'),
]