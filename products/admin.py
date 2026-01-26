from django.contrib import admin
from .models import Category, Product, Offer, CartItem, Order, OrderItem

# 1. Toto zobrazí produkty vo vnútri Objednávky
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0 # Nezobrazuje prázdne riadky navyše
    readonly_fields = ['offer', 'price', 'quantity'] # Aby sa to nedalo prepísať
    can_delete = False

# 2. Nastavenie zobrazenia Objednávky
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'full_name', 'email', 'total_price', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['full_name', 'email', 'id']
    list_editable = ['status']
    inlines = [OrderItemInline] # <--- TOTO JE KĽÚČOVÉ

# 3. Zvyšok (Produkt, Ponuky...)
class OfferInline(admin.TabularInline):
    model = Offer
    extra = 1

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category']
    search_fields = ['name']
    inlines = [OfferInline]

admin.site.register(Category)
admin.site.register(Offer)
# CartItem ani OrderItem nemusíme registrovať zvlášť, sú súčasťou iných