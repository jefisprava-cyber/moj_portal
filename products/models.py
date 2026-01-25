from django.db import models
from django.contrib.auth.models import User

class Product(models.Model):
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    shop_name = models.CharField(max_length=100)
    image_url = models.URLField(max_length=500, blank=True, null=True)
    delivery_days = models.IntegerField(default=0)
    url = models.URLField()

    def __str__(self):
        return f"{self.name} - {self.shop_name}"

    # TÁTO FUNKCIA VYTVÁRA ZISK (AFFILIATE)
    def get_affiliate_url(self):
        tvoje_affil_id = "mojportal001"
        sep = "&" if "?" in self.url else "?"
        return f"{self.url}{sep}affid={tvoje_affil_id}"

class CartItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.product.name}"

        # products/models.py

class Order(models.Model):
    # Kto objednáva (môže byť aj neprihlásený, preto user je optional)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Kontaktné údaje
    full_name = models.CharField(max_length=100, verbose_name="Celé meno")
    email = models.EmailField(verbose_name="Email")
    address = models.CharField(max_length=200, verbose_name="Adresa")
    city = models.CharField(max_length=100, verbose_name="Mesto")
    zip_code = models.CharField(max_length=10, verbose_name="PSČ")
    
    # Info o objednávke
    created_at = models.DateTimeField(auto_now_add=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    paid = models.BooleanField(default=False)

    def __str__(self):
        return f"Objednávka {self.id} - {self.full_name}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2) # Cena v čase nákupu
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.quantity}x {self.product.name}"