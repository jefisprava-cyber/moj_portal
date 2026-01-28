from django.contrib import admin
from django.urls import path
from products import views
from django.db import connection
from django.core.management import call_command
from django.http import HttpResponse

# --- RESET DB FUNKCIA ---
def reset_db_view(request):
    tables = [
        # Nové modely
        'products_planneritem', 'products_bundle', 'products_bundle_products',
        
        # Staré modely (treba ich zmazať)
        'products_orderitem', 'products_order', 'products_cartitem',
        
        # Základné
        'products_offer', 'products_product', 'products_category',
        'django_migrations', 'django_admin_log', 'django_content_type', 'django_session',
        'auth_group_permissions', 'auth_user_groups', 'auth_user_user_permissions',
        'auth_permission', 'auth_group', 'auth_user'
    ]
    
    output = []
    with connection.cursor() as cursor:
        for table in tables:
            try:
                cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")
                output.append(f"✅ Zmazaná: {table}")
            except Exception as e:
                output.append(f"⚠️ {table}: {str(e)}")
    
    try:
        call_command('migrate')
        output.append("<br><b>🚀 MIGRÁCIA NOVÝCH MODELOV ÚSPEŠNÁ</b>")
        # Vytvoríme superusera nanovo
        from django.contrib.auth.models import User
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
            output.append("<br>✅ Admin vytvorený (admin/admin123)")
    except Exception as e:
        output.append(f"<br>❌ CHYBA: {str(e)}")

    return HttpResponse("<br>".join(output))

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    
    # Dočasne necháme staré views linky, aby nepadal server, kým ich neprepíšeme
    # Alebo ich môžeme zakomentovať, ak vieš čo robíš.
    # Pre istotu nechajme len tie, čo budeme potrebovať:
    
    # path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    # path('optimize/', views.optimize_planner, name='optimize_planner'), # Premenujeme neskôr
    
    # TAJNÁ LINKA
    path('reset-db-tajny-kluc/', reset_db_view),
]