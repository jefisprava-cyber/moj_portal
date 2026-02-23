from django.contrib import admin
from .models import Product, Category, Offer, PlannerItem, Bundle, SavedPlan, SavedPlanItem

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent')
    prepopulated_fields = {'slug': ('name',)}
    # Pridané vyhľadávanie, aby fungovala lupa z iných modelov
    search_fields = ('name',)

class OfferInline(admin.TabularInline):
    model = Offer
    extra = 1

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    # 👇 TVOJE PÔVODNÉ NASTAVENIA (ZACHOVANÉ)
    list_display = ('name', 'category', 'ean', 'category_confidence', 'is_category_locked', 'is_oversized')
    
    # 👇 UPRAVENÉ: Odstránená 'category'. Vykresľovať tisíce kategórií do pravého panelu zabíjalo prehliadač!
    list_filter = ('is_category_locked', 'is_oversized')
    
    search_fields = ('name', 'ean')
    inlines = [OfferInline]

    # 🚀 👇 PRIDANÉ: TURBO ZBÝCHLENIE ADMINA 👇 🚀
    
    # 1. ZÁCHRANA DATABÁZY: Načíta produkt aj kategóriu naraz v jednom rýchlom dotaze (JOIN)
    list_select_related = ('category',)
    
    # 2. ZÁCHRANA PREHLIADAČA: Namiesto obrovskej roletky ukáže malé textové pole s lupou
    raw_id_fields = ('category',)
    
    # 3. ZÁCHRANA ČASU: Vypne zbytočné rátanie všetkých 130 000 položiek pri každom zobrazení
    show_full_result_count = False

@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = ('shop_name', 'product', 'price', 'active')
    list_filter = ('shop_name', 'active')
    # OCHRANA: Aby sa nesnažilo načítať 130k produktov do roletky!
    raw_id_fields = ('product',)

@admin.register(PlannerItem)
class PlannerItemAdmin(admin.ModelAdmin):
    list_display = ('product', 'quantity', 'user', 'session_key')
    # OCHRANA: Aby sa nesnažilo načítať 130k produktov do roletky!
    raw_id_fields = ('product',)

@admin.register(Bundle)
class BundleAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    filter_horizontal = ('products',)
    # OCHRANA PRE BUNDLE
    raw_id_fields = ('products',)

# --- Uložené plány ---
class SavedPlanItemInline(admin.TabularInline):
    model = SavedPlanItem
    extra = 0
    # OCHRANA PRE INLINE: Inak by ťa uloženie plánu stálo pád prehliadača
    raw_id_fields = ('product',)

@admin.register(SavedPlan)
class SavedPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'created_at')
    inlines = [SavedPlanItemInline]