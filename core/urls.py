from django.contrib import admin
from django.urls import path
from products import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    
    # Vyhľadávanie
    path('search/', views.search, name='search'),

    # Kategórie (NOVÉ)
    path('category/<slug:slug>/', views.category_detail, name='category_detail'),

    # Produkty a Zostavy
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('bundle/<slug:bundle_slug>/', views.bundle_detail, name='bundle_detail'),
    
    # Plánovač
    path('add/<int:product_id>/', views.add_to_planner, name='add_to_planner'),
    path('add-bundle/<int:bundle_id>/', views.add_bundle_to_planner, name='add_bundle_to_planner'),
    path('planner/', views.planner_view, name='planner_view'),
    path('remove/<int:item_id>/', views.remove_from_planner, name='remove_from_planner'),
    
    # Porovnanie
    path('compare/', views.comparison, name='comparison'),
]