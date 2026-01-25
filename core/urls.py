from django.contrib import admin
from django.urls import path, include
from products import views
from django.contrib.auth import views as auth_views # Pridaj tento import

urlpatterns = [
    path('admin/', admin.site.core),
    path('', views.home, name='home'),
    path('add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.cart_detail, name='cart_detail'),
    path('remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('optimize/', views.optimize_cart, name='optimize_cart'),
    path('register/', views.register, name='register'),
    
    # TENTO RIADOK CHÝBAL:
    path('accounts/', include('django.contrib.auth.urls')), 
]