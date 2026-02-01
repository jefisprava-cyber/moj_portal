from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify 
import random

# --- KATEGÓRIE (Stromová štruktúra) ---
class Category(models.Model):
    name = models.CharField(max_length=200, verbose_name="Názov kategórie")
    slug = models.SlugField(unique=True, blank=True, max_length=255)
    
    # Väzba na rodiča (umožňuje podkategórie: Nábytok -> Obývačka -> Sedačky)
    parent = models.ForeignKey(
        'self', 
        null=True, 
        blank=True, 
        related_name='children', 
        on_delete=models.CASCADE,
        verbose_name="Nadradená kategória"
    )

    class Meta:
        verbose_name = "Kategória"
        verbose_name_plural = "Kategórie"
        ordering = ('parent__name', 'name',)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
            # Ošetrenie duplicity slugu
            if Category.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{self.slug}-{random.randint(100, 999)}"
        super().save(*args, **kwargs)

    def __str__(self):
        # Vypíše celú cestu: "Nábytok -> Obývačka -> Sedačky"
        full_path = [self.name]
        k = self.parent
        while k is not None:
            full_path.append(k.name)
            k = k.parent
        return ' -> '.join(full_path[::-1])

# --- PRODUKTY ---
class Product(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True, max_length=255)
    description = models.TextField(blank=True)
    
    # Hlavná cena produktu (zvyčajne najnižšia cena z ponúk) - pre rýchle triedenie
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Cena od")
    
    image_url = models.URLField(max_length=1000, blank=True, null=True)
    ean = models.CharField(max_length=13, blank=True, null=True)
    
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    
    # DÔLEŽITÉ PRE IMPORT: Sem sa uloží text z feedu (napr. "Dom | Záhrada | Stoličky")
    original_category_text = models.CharField(max_length=500, blank=True, null=True)
    
    is_oversized = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Pole pre konfigurátor
    brand = models.CharField(max_length=100, blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            self.slug = base_slug
            # Bezpečné generovanie unikátneho slugu
            if Product.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{base_slug}-{random.randint(1000, 9999)}"
        
        # Automatické doplnenie značky (ak chýba, vezme prvé slovo z názvu)
        if not self.brand and self.name:
             self.brand = self.name.split()[0]

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    
    @property
    def min_price(self):
        # Vráti cenu uloženú v modeli (rýchlejšie ako query na Offers)
        return self.price

# --- PONUKY (Offers) ---
class Offer(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='offers')
    shop_name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    url = models.URLField(max_length=1000)
    delivery_days = models.IntegerField(default=0)
    active = models.BooleanField(default=True)
    external_item_id = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"{self.shop_name} - {self.product.name} ({self.price} €)"

# --- PLÁNOVAČ (Nákupný zoznam) ---
class PlannerItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=40, null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.quantity}x {self.product.name}"

# --- BALÍČKY (Bundles) ---
class Bundle(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    products = models.ManyToManyField(Product, related_name='bundles')
    image_url = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.name

# --- ULOŽENÉ PLÁNY (Sety užívateľov) ---
class SavedPlan(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_plans')
    name = models.CharField(max_length=200, default="Môj projekt")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.created_at.strftime('%d.%m.%Y')})"

class SavedPlanItem(models.Model):
    plan = models.ForeignKey(SavedPlan, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.product.name} ({self.quantity}x)"

# --- HISTÓRIA CIEN ---
class PriceHistory(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='price_history')
    min_price = models.DecimalField(max_digits=10, decimal_places=2)
    avg_price = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()

    class Meta:
        ordering = ['date']

    def __str__(self):
        return f"{self.product.name} - {self.min_price} € ({self.date})"