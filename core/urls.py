from django.contrib import admin
from django.urls import path, include
from products.views import home, add_to_cart, cart_detail, optimize_cart, register, remove_from_cart

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('register/', register, name='register'),
    path('', home, name='home'),
    path('add/<int:product_id>/', add_to_cart, name='add_to_cart'),
    path('remove/<int:item_id>/', remove_from_cart, name='remove_from_cart'),
    path('cart/', cart_detail, name='cart_detail'),
    path('optimize/', optimize_cart, name='optimize_cart'),
]