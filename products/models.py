from django.db import models
from django.contrib.auth.models import User

# 1. KATEGÓRIE
class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True) 
    parent = models.ForeignKey('self', blank=True, null=True, related_name='children', on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name

# 2. HLAVNÁ KARTA PRODUKTU (Nemá cenu, len názov a obrázok)
class Product(models.Model):
    name = models.CharField(max_length=255)
    category = models.ForeignKey(Category, related_name='products', on_delete=models.CASCADE, null=True, blank=True)
    image_url = models.URLField(max_length=500, blank=True, null=True)

    def __str__(self):
        return self.name

# 3. KONKRÉTNA PONUKA E-SHOPU (Toto má cenu a tlačidlo kúpiť)
class Offer(models.Model):
    product = models.ForeignKey(Product, related_name='offers', on_delete=models.CASCADE)
    shop_name = models.CharField(max_length=255) # Alza, Nay...
    price = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_days = models.IntegerField(default=3)
    url = models.URLField(max_length=500, blank=True, null=True)

    def __str__(self):
        return f"{self.shop_name} - {self.price}€"

# --- KOŠÍK (Teraz obsahuje Offer, nie Product) ---
class CartItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE) 
    added_at = models.DateTimeField(auto_now_add=True)

# --- OBJEDNÁVKA ---
class Order(models.Model):
    STATUS_CHOICES = (
        ('nova', 'Nová / Prijatá'),
        ('spracovava_sa', 'Spracováva sa'),
        ('odoslana', 'Odoslaná'),
        ('dorucena', 'Doručená'),
        ('zrusena', 'Zrušená'),
    )
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    full_name = models.CharField(max_length=100)
    email = models.EmailField()
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    zip_code = models.CharField(max_length=20)
    note = models.TextField(blank=True, null=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='nova')
    paid = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Objednávka #{self.id} - {self.full_name}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)