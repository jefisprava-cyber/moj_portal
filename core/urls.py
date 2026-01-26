from django.contrib import admin
from django.urls import path
from products import views  # Importujeme views z aplikácie products

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Hlavná stránka
    path('', views.home, name='home'),
    
    # Detail produktu
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    
    # --- TOTO JE TÁ KĽÚČOVÁ ZMENA ---
    # Musí tu byť 'offer_id', nie 'product_id', lebo funkcia add_to_cart to tak čaká
    path('add/<int:offer_id>/', views.add_to_cart, name='add_to_cart'),
    # --------------------------------
    
    # Ostatné cesty pre košík a objednávku
    path('remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/', views.cart_detail, name='cart_detail'),
    path('checkout/', views.checkout, name='checkout'),
    path('optimize/', views.optimize_cart, name='optimize_cart'),
    
    # Registrácia
    path('register/', views.register, name='register'),
]