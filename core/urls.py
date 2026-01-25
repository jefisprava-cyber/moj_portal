from django.contrib import admin
from django.urls import path, include
from products import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    # POZOR: Tu musí byť admin.site.urls
    path('admin/', admin.site.urls), 
    
    path('', views.home, name='home'),
    path('add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.cart_detail, name='cart_detail'),
    path('remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('optimize/', views.optimize_cart, name='optimize_cart'),
    
    # Registrácia
    path('register/', views.register, name='register'),
    
    # Autentifikácia (login, logout atď.)
    path('accounts/', include('django.contrib.auth.urls')), 
]