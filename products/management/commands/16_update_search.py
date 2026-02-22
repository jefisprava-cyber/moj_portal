import time
from django.core.management.base import BaseCommand
from products.models import Product
from django.contrib.postgres.search import SearchVector

class Command(BaseCommand):
    help = 'Naplní GIN index (search_vector) ultra-bezpečne podľa ID.'

    def handle(self, *args, **kwargs):
        self.stdout.write("🚀 Štartujem ULTRA bezpečné budovanie registra po malých krokoch...")
        start_time = time.time()
        
        vector = (
            SearchVector('name', weight='A') + 
            SearchVector('brand', weight='B') + 
            SearchVector('original_category_text', weight='C')
        )
        
        # Extrémne rýchle zistenie minimálneho a maximálneho ID v databáze
        first_product = Product.objects.order_by('id').first()
        last_product = Product.objects.order_by('-id').first()
        
        if not first_product:
            self.stdout.write("Žiadne produkty v databáze.")
            return

        min_id = first_product.id
        max_id = last_product.id
        chunk_size = 1000  # Iba 1000 kusov naraz pre absolútnu istotu
        
        total_updated = 0
        
        # Cyklus, ktorý ide od najmenšieho ID po najväčšie
        for current_min in range(min_id, max_id + 1, chunk_size):
            current_max = current_min + chunk_size - 1
            
            # Bezpečný UPDATE len v presnom rozsahu ID
            updated = Product.objects.filter(
                id__gte=current_min, 
                id__lte=current_max
            ).update(search_vector=vector)
            
            total_updated += updated
            
            if updated > 0:
                self.stdout.write(f"   🔄 Spracované ID {current_min} až {current_max} (Zatiaľ hotovo: {total_updated} ks)...")

        self.stdout.write(self.style.SUCCESS(f"🎉 HOTOVO! Zaindexovaných {total_updated} produktov."))
        self.stdout.write(f"🏁 Celkový čas: {time.time() - start_time:.2f} s")