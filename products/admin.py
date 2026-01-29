from django.contrib import admin
from .models import Product, Category, Offer, PlannerItem, Bundle, SavedPlan, SavedPlanItem

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent')
    prepopulated_fields = {'slug': ('name',)}

class OfferInline(admin.TabularInline):
    model = Offer
    extra = 1

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'ean', 'is_oversized')
    list_filter = ('category', 'is_oversized')
    search_fields = ('name', 'ean')
    inlines = [OfferInline]

@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = ('shop_name', 'product', 'price', 'active')
    list_filter = ('shop_name', 'active')

@admin.register(PlannerItem)
class PlannerItemAdmin(admin.ModelAdmin):
    list_display = ('product', 'quantity', 'user', 'session_key')

@admin.register(Bundle)
class BundleAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    filter_horizontal = ('products',)

# --- Uložené plány ---
class SavedPlanItemInline(admin.TabularInline):
    model = SavedPlanItem
    extra = 0

@admin.register(SavedPlan)
class SavedPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'created_at')
    inlines = [SavedPlanItemInline]