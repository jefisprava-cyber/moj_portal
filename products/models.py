from django.db import models
from django.contrib.auth.models import User

class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='children')

    def __str__(self):
        return self.name

class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=200)
    image_url = models.URLField(max_length=500, blank=True, null=True)

    def __str__(self):
        return self.name

class Offer(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='offers')
    shop_name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_days = models.IntegerField()
    url = models.URLField(max_length=500)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.shop_name} - {self.product.name} ({self.price}€)"

class CartItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

# --- TU BOLA ZMENA ---
class Order(models.Model):
    # Možnosti dopravy patria SEM (do celej objednávky)
    DELIVERY_CHOICES = [
        ('courier', 'Kuriér na adresu (+4.90 € / balík)'),
        ('box', 'Výdajné miesto / Box (+2.90 € / balík)'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    customer_name = models.CharField(max_length=200)
    customer_email = models.EmailField()
    
    # Toto pole použijeme na adresu domu ALEBO názov Boxu
    customer_address = models.TextField() 
    
    # Nové pole pre výber dopravy
    delivery_method = models.CharField(max_length=20, choices=DELIVERY_CHOICES, default='courier')
    
    created_at = models.DateTimeField(auto_now_add=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    note = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Objednávka {self.id} - {self.customer_name}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    offer = models.ForeignKey(Offer, on_delete=models.SET_NULL, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.IntegerField(default=1)