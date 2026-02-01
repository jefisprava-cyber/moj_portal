from django.contrib.sitemaps import Sitemap
from .models import Product

class ProductSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return Product.objects.all().order_by('-created_at')

    def lastmod(self, obj):
        return obj.created_at
        
    def location(self, obj):
        return f"/produkt/{obj.slug}/"