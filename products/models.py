from django.db import models
from django.contrib.auth.models import User

# --- MODEL PRE PRODUKTY ---
class Product(models.Model):
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    shop_name = models.CharField(max_length=255)
    delivery_days = models.IntegerField(default=3)
    image_url = models.URLField(max_length=500, blank=True, null=True)
    url = models.URLField(max_length=500, blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.shop_name})"

# --- MODEL PRE KOŠÍK ---
class CartItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Košík: {self.product.name}"

# --- MODEL PRE OBJEDNÁVKU ---
class Order(models.Model):
    # Definícia stavov objednávky
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
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    paid = models.BooleanField(default=False)
    
    # NOVÉ: Stav objednávky
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='nova')
    
    # NOVÉ: Poznámka pre predajcu
    note = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Objednávka #{self.id} - {self.full_name}"

# --- MODEL PRE POLOŽKY V OBJEDNÁVKE ---
class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.quantity}x {self.product.name}"

    def get_total_item_price(self):
        return self.price * self.quantity