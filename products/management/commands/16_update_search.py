import time
from django.core.management.base import BaseCommand
from products.models import Product
from django.contrib.postgres.search import SearchVector

class Command(BaseCommand):
    help = 'Naplní GIN index (search_vector) pre bleskové vyhľadávanie.'

    def handle(self, *args, **kwargs):
        self.stdout.write("🚀 Štartujem budovanie Full-Text registra (Fáza 2)...")
        start_time = time.time()
        
        # Databáze prikážeme vytvoriť slovník:
        # Názov má najvyššiu prioritu 'A', Značka 'B' a kategória od dodávateľa 'C'
        vector = (
            SearchVector('name', weight='A') + 
            SearchVector('brand', weight='B') + 
            SearchVector('original_category_text', weight='C')
        )
        
        # Toto vykoná JEDEN obrovský príkaz priamo vo vnútri PostgreSQL, 
        # čo je asi 1000x rýchlejšie, než keby sme to robili cez Python (for cyklus).
        updated_count = Product.objects.update(search_vector=vector)
        
        self.stdout.write(self.style.SUCCESS(f"🎉 HOTOVO! Raketovo zaindexovaných {updated_count} produktov."))
        self.stdout.write(f"🏁 Celkový čas indexácie: {time.time() - start_time:.2f} s")