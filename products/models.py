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
    
    # --- NOVÉ POLIA PRE XML IMPORTY ---
    # EAN: Unikátny čiarový kód, podľa ktorého budeme párovať produkty z rôznych e-shopov
    ean = models.CharField(max_length=13, blank=True, null=True, unique=True)
    
    # Popis: Dlhý text z feedu pre SEO
    description = models.TextField(blank=True, null=True)
    
    image_url = models.URLField(max_length=500, blank=True, null=True)
    
    # Logika pre dopravu (Veľké produkty len kuriérom)
    is_oversized = models.BooleanField(default=False, verbose_name="Nadrozmerný tovar (len kuriér)")

    def __str__(self):
        return self.name

class Offer(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='offers')
    shop_name = models.CharField(max_length=100)
    
    # --- NOVÉ POLIA PRE UPDATE CIEN ---
    # ID produktu v cudzom e-shope (aby sme vedeli aktualizovať cenu a nevytvárali duplicity)
    external_item_id = models.CharField(max_length=100, blank=True, null=True)
    
    price = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_days = models.IntegerField(default=0)
    url = models.URLField(max_length=1000)
    active = models.BooleanField(default=True)
    
    # Kedy sme naposledy kontrolovali cenu
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        # Zabezpečíme, že jeden obchod nemôže mať 2x ten istý produkt (cez ID)
        unique_together = ('shop_name', 'external_item_id')

    def __str__(self):
        return f"{self.shop_name} - {self.product.name} ({self.price}€)"

class CartItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

class Order(models.Model):
    # Možnosti dopravy pre celú objednávku
    DELIVERY_CHOICES = [
        ('courier', 'Kuriér na adresu (+4.90 €)'),
        ('box', 'Výdajné miesto / Box (+2.90 €)'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    customer_name = models.CharField(max_length=200)
    customer_email = models.EmailField()
    customer_address = models.TextField() 
    
    # Výber dopravy
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