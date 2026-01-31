from django.contrib import admin
from django.urls import path
from products import views
from django.contrib.auth import views as auth_views
from django.contrib.sitemaps.views import sitemap # <--- Import
from products.sitemaps import ProductSitemap    # <--- Import

# Definícia sitemáp
sitemaps = {
    'products': ProductSitemap,
}

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    
    # SITEMAP (PRE GOOGLE)
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),

    # SEO URL PRODUKTU
    path('p/<slug:slug>/', views.product_detail, name='product_detail'),

    # OSTATNÉ
    path('search/', views.search, name='search'),
    path('category/<slug:slug>/', views.category_detail, name='category_detail'),
    path('bundle/<slug:bundle_slug>/', views.bundle_detail, name='bundle_detail'),
    
    # AUTH & PLANNER
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    path('register/', views.register, name='register'),
    path('profile/', views.profile, name='profile'),
    path('save-plan/', views.save_current_plan, name='save_current_plan'),
    path('load-plan/<int:plan_id>/', views.load_plan, name='load_plan'),
    path('delete-plan/<int:plan_id>/', views.delete_plan, name='delete_plan'),
    
    path('add/<int:product_id>/', views.add_to_planner, name='add_to_planner'),
    path('add-bundle/<int:bundle_id>/', views.add_bundle_to_planner, name='add_bundle_to_planner'),
    path('planner/', views.planner_view, name='planner_view'),
    path('remove/<int:item_id>/', views.remove_from_planner, name='remove_from_planner'),
    path('compare/', views.comparison, name='comparison'),
]