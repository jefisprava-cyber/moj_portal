from django.contrib import admin
from django.urls import path, include
from products import views
from django.contrib.auth import views as auth_views
from django.contrib.sitemaps.views import sitemap
from products.sitemaps import ProductSitemap
from django.views.generic import TemplateView

# Definícia sitemáp
sitemaps = {
    'products': ProductSitemap,
}

urlpatterns = [
    # --- ADMIN A CORE ---
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('accounts/', include('django.contrib.auth.urls')),

    # --- PRÁVNE STRÁNKY (GDPR, COOKIES, VOP) ---
    path('ochrana-udajov/', TemplateView.as_view(template_name='pages/gdpr.html'), name='gdpr'),
    path('obchodne-podmienky/', TemplateView.as_view(template_name='pages/vop.html'), name='vop'),
    path('cookies/', TemplateView.as_view(template_name='pages/cookies.html'), name='cookies'),
    
    # Fallback pre staré odkazy
    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),

    # --- VYHĽADÁVANIE A POROVNANIE (Dávame vyššie pred produktový slug) ---
    path('hladat/', views.search, name='search'),  # Zmenené na 'hladat/' pre slovenčinu
    path('compare/', views.comparison, name='comparison'),

    # --- NOVÉ: INTELIGENTNÝ KONFIGURÁTOR ---
    path('inteligentny-konfigurator/', views.builder_view, name='builder'),
    # API pre konfigurátor
    path('api/brands/<int:category_id>/', views.api_get_brands, name='api_get_brands'),
    path('api/products/<int:category_id>/', views.api_get_products, name='api_get_products'),

    # --- NOVÉ: UŽÍVATEĽSKÉ SETY (GARÁŽ PROJEKTOV) ---
    path('moje-sety/', views.my_sets_view, name='my_sets'),
    path('set/ulozit/', views.save_builder_set, name='save_builder_set'),
    path('set/nahrat/<int:set_id>/', views.load_set, name='load_set'),
    path('set/zmazat/<int:set_id>/', views.delete_set, name='delete_set'),

    # --- NOVÉ: AUTOMATICKÝ IMPORT ---
    path('import-data/', views.trigger_import, name='trigger_import'),

    # --- KATEGÓRIE A BALÍČKY ---
    path('category/<slug:slug>/', views.category_detail, name='category_detail'),
    path('bundle/<slug:bundle_slug>/', views.bundle_detail, name='bundle_detail'),

    # --- SEO & DETAIL PRODUKTU ---
    # Toto dávame naschvál nižšie, aby 'p/nieco' neodchytilo iné špeciálne URL
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('p/<slug:slug>/', views.product_detail, name='product_detail'),

    # --- PRIHLASOVANIE A PROFIL ---
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    path('register/', views.register, name='register'),
    path('profile/', views.profile, name='profile'),

    # --- KOŠÍK / PLÁNOVAČ ---
    path('planner/', views.planner_view, name='planner_view'),
    path('add/<int:product_id>/', views.add_to_planner, name='add_to_planner'),
    path('add-bundle/<int:bundle_id>/', views.add_bundle_to_planner, name='add_bundle_to_planner'),
    path('remove/<int:item_id>/', views.remove_from_planner, name='remove_from_planner'),
    
    # --- STARÉ ULOŽENIE A NAČÍTANIE (Pre kompatibilitu) ---
    path('save-plan/', views.save_current_plan, name='save_current_plan'),
    path('load-plan/<int:plan_id>/', views.load_plan, name='load_plan'),
    path('delete-plan/<int:plan_id>/', views.delete_plan, name='delete_plan'),
]