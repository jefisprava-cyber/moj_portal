from django.contrib import admin
from django.utils.safestring import mark_safe
from .models import Category, Product, Offer, CartItem, Order, OrderItem

# Ponuky sa editujú priamo vnútri Produktu
class OfferInline(admin.TabularInline):
    model = Offer
    extra = 1
    fields = ['shop_name', 'price', 'delivery_days', 'url']

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'count_offers', 'cheapest_price_display']
    list_filter = ['category']
    search_fields = ['name']
    inlines = [OfferInline] # Toto zobrazí ponuky v detaile produktu

    def count_offers(self, obj):
        return obj.offers.count()
    count_offers.short_description = "Počet e-shopov"

    def cheapest_price_display(self, obj):
        cheapest = obj.get_cheapest_offer()
        return f"{cheapest.price} €" if cheapest else "-"
    cheapest_price_display.short_description = "Najlepšia cena"

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'status', 'full_name', 'total_price', 'created_at']
    list_editable = ['status']
    inlines = [] # Položky riešime nižšie

    # Keďže sme zmenili OrderItem, musíme si tu spraviť vlastný inline alebo to nechať tak
    # Pre jednoduchosť to zatiaľ necháme bez inline editácie položiek, len základ

admin.site.register(Category)
admin.site.register(Offer)
admin.site.register(CartItem)