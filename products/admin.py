from django.contrib import admin
from .models import Category, Product, Offer, CartItem, Order, OrderItem

# 1. TOTO ZABEZPEČÍ ZOBRAZENIE POLOŽIEK V OBJEDNÁVKE
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['offer_link', 'price', 'quantity']
    can_delete = False
    
    # Trik, aby si v admine videl aj priamy preklik na e-shop (ak to budeš objednávať ty)
    def offer_link(self, obj):
        return f"{obj.offer.product.name} ({obj.offer.shop_name})"
    offer_link.short_description = "Tovar"

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'full_name', 'email', 'total_price', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['full_name', 'email']
    list_editable = ['status']
    inlines = [OrderItemInline] # <--- Toto pridá tabuľku produktov do detailu objednávky

# 2. NASTAVENIE PRODUKTOV A PONÚK
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
# CartItem neregistrujeme, je to dočasné