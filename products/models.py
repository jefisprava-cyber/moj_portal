from django.db import models
from django.contrib.auth.models import User

# --- KATEGÓRIE A PRODUKTY ---
class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='children')

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name

class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=200)
    
    # Identifikácia pre importy
    ean = models.CharField(max_length=13, blank=True, null=True, unique=True)
    description = models.TextField(blank=True, null=True)
    image_url = models.URLField(max_length=500, blank=True, null=True)
    
    # Príznak pre logistiku (aj keď len odkazujeme, je dobré vedieť, že to je veľké)
    is_oversized = models.BooleanField(default=False, verbose_name="Nadrozmerný tovar")

    def __str__(self):
        return self.name

# --- PONUKY (Ceny z XML feedov) ---
class Offer(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='offers')
    shop_name = models.CharField(max_length=100) # Napr. Alza, Nay, Datart
    
    # ID v cudzom systéme
    external_item_id = models.CharField(max_length=100, blank=True, null=True)
    
    price = models.DecimalField(max_digits=10, decimal_places=2)
    
    # TOTO JE NAJDÔLEŽITEJŠIE: Affiliate Link
    url = models.URLField(max_length=1000) 
    
    delivery_days = models.IntegerField(default=0)
    active = models.BooleanField(default=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('shop_name', 'external_item_id')

    def __str__(self):
        return f"{self.shop_name} - {self.product.name} ({self.price}€)"

# --- PREDVOLENÉ ZOSTAVY (Smart funkcia) ---
class Bundle(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    image_url = models.URLField(blank=True, null=True)
    
    # Zostava obsahuje veľa produktov
    products = models.ManyToManyField(Product, related_name='bundles')
    
    def __str__(self):
        return self.name

# --- NÁKUPNÝ PLÁNOVAČ (Namiesto košíka) ---
class PlannerItem(models.Model):
    # Môže patriť prihlásenému Userovi...
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    
    # ...alebo neprihlásenému hosťovi (podľa session ID)
    session_key = models.CharField(max_length=40, null=True, blank=True)
    
    # Ukladáme PRODUKT (všeobecne), nie Offer (konkrétny obchod)
    # Rozhodnutie "odkiaľ kúpiť" robíme až vo výpočte
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"Plan: {self.product.name} ({self.quantity}x)"