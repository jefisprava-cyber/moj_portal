from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify 
from django.db.models import Avg
import random

# --- KATEGÓRIE (Stromová štruktúra) ---
class Category(models.Model):
    name = models.CharField(max_length=200, verbose_name="Názov kategórie")
    slug = models.SlugField(unique=True, blank=True, max_length=255)
    
    parent = models.ForeignKey(
        'self', 
        null=True, 
        blank=True, 
        related_name='children', 
        on_delete=models.CASCADE,
        verbose_name="Nadradená kategória"
    )

    is_active = models.BooleanField(default=False, verbose_name="Viditeľná na webe")

    class Meta:
        verbose_name = "Kategória"
        verbose_name_plural = "Kategórie"
        ordering = ('parent__name', 'name',)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
            if Category.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{self.slug}-{random.randint(100, 999)}"
        super().save(*args, **kwargs)

    def __str__(self):
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
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Cena od")
    image_url = models.URLField(max_length=1000, blank=True, null=True)
    ean = models.CharField(max_length=13, blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    
    # 👇 TOTO JE KĽÚČOVÉ POLE PRE SMART MAPPER 👇
    original_category_text = models.CharField(max_length=500, blank=True, null=True)
    
    is_oversized = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    brand = models.CharField(max_length=100, blank=True, null=True)
    average_rating = models.FloatField(default=0.0)
    review_count = models.IntegerField(default=0)

    @property
    def get_image(self):
        if self.image_url and self.image_url.startswith('http') and 'via.placeholder.com' not in self.image_url:
            return self.image_url
        return "https://placehold.co/500x500?text=Bez+obrazka"

    def recalculate_rating(self):
        reviews = self.reviews.all()
        if reviews.exists():
            self.average_rating = reviews.aggregate(Avg('rating'))['rating__avg']
            self.review_count = reviews.count()
        else:
            self.average_rating = 0.0
            self.review_count = 0
        self.save()

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            self.slug = base_slug
            if Product.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{base_slug}-{random.randint(1000, 9999)}"
        if not self.brand and self.name:
             self.brand = self.name.split()[0]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

# --- PARAMETRE PRODUKTOV ---
class ProductParameter(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='parameters')
    name = models.CharField(max_length=100, db_index=True)
    value = models.CharField(max_length=100, db_index=True)

    def __str__(self):
        return f"{self.product.name} - {self.name}: {self.value}"

# --- PONUKY (Offers) ---
class Offer(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='offers')
    shop_name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    url = models.URLField(max_length=1000)
    delivery_days = models.IntegerField(default=0)
    active = models.BooleanField(default=True)
    external_item_id = models.CharField(max_length=100, blank=True)
    is_sponsored = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.shop_name} - {self.product.name} ({self.price} €)"

# --- PLÁNOVAČ ---
class PlannerItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=40, null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.quantity}x {self.product.name}"

# --- BALÍČKY ---
class Bundle(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    products = models.ManyToManyField(Product, related_name='bundles')
    image_url = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.name

# --- ULOŽENÉ PLÁNY ---
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

# --- RECENZIE ---
class Review(models.Model):
    product = models.ForeignKey(Product, related_name='reviews', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.product.recalculate_rating()