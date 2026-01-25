from django.contrib import admin
from django.utils.safestring import mark_safe
from .models import Product, CartItem, Order, OrderItem

# 1. Zobrazenie položiek v objednávke s tlačidlom priamo do e-shopu
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    # 'go_to_shop' je naša nová funkcia nižšie
    fields = ['product', 'price', 'quantity', 'go_to_shop']
    readonly_fields = ['product', 'price', 'quantity', 'go_to_shop']

    def go_to_shop(self, obj):
        if obj.product.url:
            return mark_safe(f'<a href="{obj.product.url}" target="_blank" style="background: #2563eb; color: white; padding: 5px 10px; border-radius: 6px; text-decoration: none; font-weight: bold; font-size: 11px;">🔗 OTVORIŤ E-SHOP</a>')
        return "Bez odkazu"
    
    go_to_shop.short_description = 'Akcia'

# 2. Hlavná správa objednávok
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    # Čo uvidíš v zozname všetkých objednávok
    list_display = ['id', 'status', 'full_name', 'total_price', 'created_at', 'paid']
    # Možnosť prepnúť stav a platbu priamo v zozname (bez rozkliknutia)
    list_editable = ['status', 'paid']
    list_filter = ['status', 'paid', 'created_at']
    search_fields = ['full_name', 'email', 'id']
    inlines = [OrderItemInline]
    
    # Usporiadanie polí v detaile objednávky do logických blokov
    fieldsets = (
        ('Stav objednávky', {
            'fields': ('status', 'paid', 'total_price', 'created_at')
        }),
        ('Informácie o zákazníkovi', {
            'fields': ('full_name', 'email', 'address', 'city', 'zip_code')
        }),
        ('Dôležitá poznámka', {
            'fields': ('note',),
        }),
    )
    # Tieto polia nemôžeš prepísať, len vidieť
    readonly_fields = ['created_at', 'total_price']

# 3. Zobrazenie tvojich produktov s náhľadom obrázka
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'shop_name', 'image_preview']
    search_fields = ['name', 'shop_name']

    def image_preview(self, obj):
        if obj.image_url:
            return mark_safe(f'<img src="{obj.image_url}" width="40" height="40" style="border-radius: 4px;" />')
        return "-"
    image_preview.short_description = 'Obr.'

admin.site.register(CartItem)