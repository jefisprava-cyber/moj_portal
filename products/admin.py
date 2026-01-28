from django.contrib import admin
from .models import Category, Product, Offer, Order, OrderItem

# Pekné zobrazenie Produktov
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'ean', 'is_oversized') # Vidíš stĺpce
    list_editable = ('is_oversized',) # Môžeš to meniť priamo v zozname!
    search_fields = ('name', 'ean')
    list_filter = ('is_oversized', 'category')

# Pekné zobrazenie Ponúk
@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = ('product', 'shop_name', 'price', 'active')
    list_filter = ('shop_name', 'active')

# Pekné zobrazenie Objednávok
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer_name', 'total_price', 'delivery_method', 'created_at')
    inlines = [OrderItemInline]

admin.site.register(Category)