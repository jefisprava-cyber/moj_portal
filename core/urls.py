from django.contrib import admin
from django.urls import path
from products import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    
    # AUTH
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    path('register/', views.register, name='register'),
    
    # PROFIL A PLÁNY (NOVÉ)
    path('profile/', views.profile, name='profile'),
    path('save-plan/', views.save_current_plan, name='save_current_plan'),
    path('load-plan/<int:plan_id>/', views.load_plan, name='load_plan'),
    path('delete-plan/<int:plan_id>/', views.delete_plan, name='delete_plan'),

    # OSTATNÉ
    path('search/', views.search, name='search'),
    path('category/<slug:slug>/', views.category_detail, name='category_detail'),
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('bundle/<slug:bundle_slug>/', views.bundle_detail, name='bundle_detail'),
    path('add/<int:product_id>/', views.add_to_planner, name='add_to_planner'),
    path('add-bundle/<int:bundle_id>/', views.add_bundle_to_planner, name='add_bundle_to_planner'),
    path('planner/', views.planner_view, name='planner_view'),
    path('remove/<int:item_id>/', views.remove_from_planner, name='remove_from_planner'),
    path('compare/', views.comparison, name='comparison'),
]