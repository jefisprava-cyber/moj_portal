from django.contrib import admin
from django.urls import path
from products import views
# Import pre reset DB (nechávame ho tam pre istotu)
from products.views import home # len pre import
from django.db import connection
from django.core.management import call_command
from django.http import HttpResponse

# Funkcia reset DB (ak ju tam chceš nechať pre budúcnosť)
def reset_db_view(request):
    # ... (kód z minula, alebo ho vymaž ak už si resetol)
    return HttpResponse("Reset disabled for security") 

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    
    # Nákupný Plánovač
    path('add/<int:product_id>/', views.add_to_planner, name='add_to_planner'),
    path('planner/', views.planner_view, name='planner_view'),
    path('remove/<int:item_id>/', views.remove_from_planner, name='remove_from_planner'),
    
    # Výsledok porovnania
    path('compare/', views.comparison, name='comparison'),

    # Tajný reset (voliteľné)
    # path('reset-db-tajny-kluc/', reset_db_view),
]