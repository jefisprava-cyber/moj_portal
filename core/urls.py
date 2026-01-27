from django.contrib import admin
from django.urls import path
from products import views
from django.db import connection
from django.core.management import call_command
from django.http import HttpResponse

# --- TOTO JE TAJNÁ FUNKCIA NA OPRAVU DATABÁZY NA RENDERI ---
def reset_db_view(request):
    # 1. Zoznam tabuliek na zmazanie
    tables = [
        'products_cartitem', 'products_orderitem', 'products_order', 
        'products_offer', 'products_product', 'products_category',
        'django_migrations', 'auth_user', 'auth_permission', 
        'auth_group', 'django_content_type', 'django_session', 'django_admin_log'
    ]
    
    output = []
    
    # 2. Zmazanie tabuliek
    with connection.cursor() as cursor:
        for table in tables:
            try:
                cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")
                output.append(f"Zmazaná tabuľka: {table}")
            except Exception as e:
                output.append(f"Chyba pri {table}: {str(e)}")
    
    # 3. Spustenie migrácie (Vytvorenie nových tabuliek)
    try:
        call_command('migrate')
        output.append("--- MIGRÁCIA ÚSPEŠNÁ ---")
    except Exception as e:
        output.append(f"!!! CHYBA MIGRÁCIE: {str(e)}")

    return HttpResponse("<br>".join(output))

# --- URL ADRESY ---
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('add/<int:offer_id>/', views.add_to_cart, name='add_to_cart'),
    path('remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/', views.cart_detail, name='cart_detail'),
    path('optimize/', views.optimize_cart, name='optimize_cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('register/', views.register, name='register'),
    
    # TOTO JE TAJNÁ LINKA (Len dočasne)
    path('reset-db-tajny-kluc/', reset_db_view),
]