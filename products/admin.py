from django.contrib import admin
from .models import Product, CartItem, Order, OrderItem

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product', 'price', 'quantity']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'status', 'full_name', 'total_price', 'created_at', 'paid']
    list_editable = ['status', 'paid']
    list_filter = ['status', 'paid', 'created_at']
    search_fields = ['full_name', 'email', 'id']
    inlines = [OrderItemInline]
    
    # Pridáme pole 'note' do detailu objednávky, aby sa dalo čítať
    fields = ['status', 'paid', 'full_name', 'email', 'address', 'city', 'zip_code', 'total_price', 'note', 'created_at']
    readonly_fields = ['created_at', 'total_price']

admin.site.register(Product)
admin.site.register(CartItem)