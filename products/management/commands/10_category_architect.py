from django.core.management.base import BaseCommand
from products.models import Category, Product
from django.db import transaction

class Command(BaseCommand):
    help = 'ARCHITEKT: Nukleárne čistenie. Zmaže všetko okrem produktov.'

    def handle(self, *args, **kwargs):
        self.stdout.write("☢️  ARCHITEKT: Začínam čistenie databázy...")

        with transaction.atomic():
            # 1. Vytvoríme/Získame záchrannú kategóriu
            safe_cat, _ = Category.objects.get_or_create(
                slug="nezaradene-temp",
                defaults={'name': "NEZARADENÉ", 'is_active': False}
            )

            # 2. Presunieme TAM všetky produkty (aby sme o ne neprišli)
            # Produkty sa "odpoja" od starých kategórií
            total_products = Product.objects.count()
            Product.objects.all().update(category=safe_cat)
            self.stdout.write(f"📦 {total_products} produktov presunutých do bezpečia (NEZARADENÉ).")

            # 3. Zmažeme VŠETKY ostatné kategórie
            deleted_count, _ = Category.objects.exclude(id=safe_cat.id).delete()
            self.stdout.write(f"🗑️  Zmazaných {deleted_count} starých kategórií.")

        self.stdout.write(self.style.SUCCESS("✅ HOTOVO. Stôl je čistý. Teraz spusti import alebo triedič."))