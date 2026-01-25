from django.contrib import admin
from .models import Product, CartItem, Order, OrderItem

# 1. Zobrazenie položiek objednávky priamo v detaile objednávky
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    # Položky v objednávke by sa nemali meniť, tak ich dáme len na čítanie
    readonly_fields = ['product', 'price', 'quantity']

# 2. Hlavná správa objednávok
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    # Čo uvidíš v tabuľke (pridaný status)
    list_display = ['id', 'status', 'full_name', 'total_price', 'created_at', 'paid']
    
    # TOTO JE TA KÚZELNÁ ČASŤ: Tieto polia môžeš meniť priamo v zozname
    list_editable = ['status', 'paid']
    
    # Filtre na pravej strane
    list_filter = ['status', 'paid', 'created_at']
    
    # Vyhľadávanie (podľa mena, emailu alebo čísla objednávky)
    search_fields = ['full_name', 'email', 'id']
    
    # Prepojenie na položky objednávky
    inlines = [OrderItemInline]

# 3. Ostatné modely (jednoduchá registrácia)
admin.site.register(Product)
admin.site.register(CartItem)