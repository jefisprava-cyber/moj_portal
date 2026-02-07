from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'NATVRDO zmaze tabulky pre products aplikaciu (Fix pre PostgreSQL)'

    def handle(self, *args, **kwargs):
        self.stdout.write("⚠️ ZACINAM HARD RESET DATABAZY...")
        
        with connection.cursor() as cursor:
            # 1. Vymazanie tabuliek v spravnom poradi (kvoli vazbam)
            tables = [
                'products_cartitem',
                'products_orderitem',
                'products_order',
                'products_offer',   # Toto je nova tabulka, mozno neexistuje, nevadi
                'products_product',
                'products_category', # Toto je nova tabulka
            ]
            
            for table in tables:
                self.stdout.write(f"🗑️ Mazem tabulku: {table}")
                # CASCADE zabezpeci, ze sa zmazu aj prepojenia
                cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")
            
            # 2. Vymazanie historie migracii pre tuto aplikaciu
            # Toto je KLÚČOVÉ: Django si bude mysliet, ze aplikacia je nova
            self.stdout.write("🧹 Cistim historiu migracii...")
            cursor.execute("DELETE FROM django_migrations WHERE app='products';")

        self.stdout.write(self.style.SUCCESS("✅ DATABAZA JE CISTA. TERAZ SPUSTI MIGRATE."))