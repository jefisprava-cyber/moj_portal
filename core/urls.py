from django.contrib import admin
from django.urls import path
from products import views
from django.db import connection
from django.core.management import call_command
from django.http import HttpResponse

# --- TOTO JE TAJNÁ FUNKCIA NA OPRAVU DATABÁZY NA RENDERI ---
def reset_db_view(request):
    # 1. Zoznam VŠETKÝCH tabuliek na zmazanie (vrátane skrytých spojovacích)
    tables = [
        # Naše aplikácie
        'products_cartitem', 'products_orderitem', 'products_order', 
        'products_offer', 'products_product', 'products_category',
        
        # Django Admin a História
        'django_admin_log', 'django_migrations', 'django_content_type', 'django_session',
        
        # Auth (Používatelia a skupiny) - TU BOL PROBLÉM, PRIDÁVAME TIETO:
        'auth_group_permissions',       # <--- TOTO CHÝBALO
        'auth_user_groups',             # <--- AJ TOTO
        'auth_user_user_permissions',   # <--- AJ TOTO
        'auth_permission', 
        'auth_group', 
        'auth_user'
    ]
    
    output = []
    
    # 2. Zmazanie tabuliek (Hard Reset)
    with connection.cursor() as cursor:
        for table in tables:
            try:
                cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")
                output.append(f"✅ Zmazaná tabuľka: {table}")
            except Exception as e:
                output.append(f"⚠️ Chyba pri {table} (možno neexistuje): {str(e)}")
    
    # 3. Spustenie migrácie (Vytvorenie nových tabuliek)
    try:
        call_command('migrate')
        output.append("<br><br><b>--- 🚀 MIGRÁCIA ÚSPEŠNÁ! ---</b>")
        output.append("<br>Teraz je databáza čistá. Môžeš ísť na domovskú stránku.")
    except Exception as e:
        output.append(f"<br><br><b>!!! STÁLE CHYBA MIGRÁCIE: {str(e)}</b>")

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
    
    # TAJNÁ LINKA
    path('reset-db-tajny-kluc/', reset_db_view),
]