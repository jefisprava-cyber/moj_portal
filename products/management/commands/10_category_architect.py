from django.core.management.base import BaseCommand
from products.models import Category
from django.db import connection, transaction

class Command(BaseCommand):
    help = 'ARCHITEKT TURBO: Bezpečné SQL čistenie s transakčnou poistkou.'

    def handle(self, *args, **kwargs):
        self.stdout.write("☢️  ARCHITEKT: Začínam SQL čistenie...")

        # Použijeme transakciu = Ak nastane chyba, všetko sa vráti späť
        with transaction.atomic():
            
            # 1. Vytvoríme/Získame záchrannú kategóriu (cez Django ORM = bezpečné)
            safe_cat, _ = Category.objects.get_or_create(
                slug="nezaradene-temp",
                defaults={'name': "NEZARADENÉ (IMPORT)", 'is_active': False}
            )
            safe_id = safe_cat.id

            with connection.cursor() as cursor:
                # 2. ZACHRÁNIŤ PRODUKTY
                self.stdout.write("📦 Presúvam produkty do bezpečia...")
                cursor.execute(
                    "UPDATE products_product SET category_id = %s", 
                    [safe_id]
                )
                
                # 3. ROZPOJIŤ STROM (Aby neboli chyby pri mazaní rodičov)
                self.stdout.write("🪓 Ruším väzby rodič-dieťa...")
                cursor.execute("UPDATE products_category SET parent_id = NULL")

                # 4. ZMAZAŤ STARÉ KATEGÓRIE (Všetko okrem záchrannej)
                self.stdout.write("🔥 Mažem staré kategórie...")
                cursor.execute(
                    "DELETE FROM products_category WHERE id != %s", 
                    [safe_id]
                )

        self.stdout.write(self.style.SUCCESS("✅ HOTOVO. Databáza je čistá a bezpečná."))