from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify 

# --- KATEGÓRIE ---
class Category(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    parent = models.ForeignKey('self', null=True, blank=True, related_name='children', on_delete=models.CASCADE)

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Categories"

# --- PRODUKTY ---
class Product(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)
    image_url = models.URLField(blank=True, null=True)
    ean = models.CharField(max_length=13, blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    is_oversized = models.BooleanField(default=False)
    
    # --- TOTO NÁM CHÝBALO ---
    created_at = models.DateTimeField(auto_now_add=True) 
    # ------------------------

    # Pole pre konfigurátor
    brand = models.CharField(max_length=100, blank=True, null=True) 

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
            original_slug = self.slug
            counter = 1
            while Product.objects.filter(slug=self.slug).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        
        # Automatické doplnenie značky
        if not self.brand and self.name:
             self.brand = self.name.split()[0]

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

# --- PONUKY ---
class Offer(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='offers')
    shop_name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    url = models.URLField()
    delivery_days = models.IntegerField(default=0)
    active = models.BooleanField(default=True)
    external_item_id = models.CharField(max_length=100, blank=True)

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