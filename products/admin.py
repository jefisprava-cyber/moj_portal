from django.contrib import admin
from .models import Category, Product, Offer, Bundle, PlannerItem

# 1. Kategórie
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'parent')
    prepopulated_fields = {'slug': ('name',)}

# 2. Produkty (Pridané EAN a Oversized)
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'ean', 'is_oversized')
    list_editable = ('is_oversized',)
    search_fields = ('name', 'ean')
    list_filter = ('is_oversized', 'category')

# 3. Ponuky (Affiliate linky)
@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = ('product', 'shop_name', 'price', 'active', 'last_updated')
    list_filter = ('shop_name', 'active')
    search_fields = ('product__name', 'url')

# 4. NOVINKA: Zostavy / Bundles
@admin.register(Bundle)
class BundleAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    # filter_horizontal urobí pekný výber produktov (vľavo dostupné, vpravo vybraté)
    filter_horizontal = ('products',)

# 5. Nákupný Plánovač (Len na kontrolu, čo si ľudia ukladajú)
@admin.register(PlannerItem)
class PlannerItemAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'session_key', 'quantity')
    