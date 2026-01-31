from django.contrib.sitemaps import Sitemap
from .models import Product

class ProductSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.8

    def items(self):
        return Product.objects.all()

    def lastmod(self, obj):
        # Ak by sme mali pole updated_at, použili by sme to.
        # Teraz vrátime None, Google si to zistí sám.
        return None 
        
    def location(self, obj):
        return f"/p/{obj.slug}/"