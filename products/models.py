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