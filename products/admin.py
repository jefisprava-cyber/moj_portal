from django.contrib import admin
from .models import Product, CartItem, Order, OrderItem

# Registrácia existujúcich modelov
admin.site.register(Product)
admin.site.register(CartItem)

# --- NOVÉ: Registrácia objednávok ---
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'full_name', 'email', 'total_price', 'created_at', 'paid']
    list_filter = ['paid', 'created_at']
    inlines = [OrderItemInline]