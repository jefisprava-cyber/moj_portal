from django.core.management.base import BaseCommand
from products.models import Product

class Command(BaseCommand):
    help = 'Vyčistí škaredé technické popisy (napr. ONL.D...)'

    def handle(self, *args, **kwargs):
        self.stdout.write("🧹 Začínam čistenie popisov...")

        # 1. Hľadáme produkty, ktoré začínajú na tie technické kódy
        ugly_products = Product.objects.filter(description__startswith="ONL.D") | \
                        Product.objects.filter(description__startswith="TYP:") | \
                        Product.objects.filter(description__icontains="MELAM.GRAU")

        count = ugly_products.count()
        self.stdout.write(f"Nájdených {count} produktov so škaredým popisom.")

        # 2. Vymažeme popis (alebo nahradíme textom "Popis pripravujeme")
        # Používame update() pre rýchlosť
        ugly_products.update(description="") 

        self.stdout.write(self.style.SUCCESS(f"✅ HOTOVO. {count} popisov bolo vyčistených."))