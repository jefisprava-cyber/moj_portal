import time
from django.core.management.base import BaseCommand
from products.models import Product
from django.contrib.postgres.search import SearchVector
from django.core.paginator import Paginator

class Command(BaseCommand):
    help = 'Naplní GIN index (search_vector) bezpečne po dávkach.'

    def handle(self, *args, **kwargs):
        self.stdout.write("🚀 Štartujem bezpečné budovanie registra po dávkach...")
        start_time = time.time()
        
        vector = (
            SearchVector('name', weight='A') + 
            SearchVector('brand', weight='B') + 
            SearchVector('original_category_text', weight='C')
        )
        
        # Zoradíme produkty podľa ID a rozdelíme na dávky po 5000 (Paginator)
        products = Product.objects.all().order_by('id')
        paginator = Paginator(products, 5000)
        
        total_updated = 0
        
        for page in paginator.page_range:
            # Vytiahneme si len IDčka pre túto konkrétnu dávku
            batch_ids = list(paginator.page(page).object_list.values_list('id', flat=True))
            
            # Bezpečne updatneme len túto malú dávku (nehrozí Deadlock)
            Product.objects.filter(id__in=batch_ids).update(search_vector=vector)
            
            total_updated += len(batch_ids)
            self.stdout.write(f"   🔄 Dávka {page}/{paginator.num_pages} ({total_updated} produktov)...")

        self.stdout.write(self.style.SUCCESS(f"🎉 HOTOVO! Bezpečne zaindexovaných {total_updated} produktov."))
        self.stdout.write(f"🏁 Celkový čas: {time.time() - start_time:.2f} s")