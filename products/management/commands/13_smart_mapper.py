# products/management/commands/13_smart_mapper.py
from django.core.management.base import BaseCommand
from products.models import Product, Category
from django.db.models import Q
from thefuzz import process, fuzz  # Knižnica na podobnosť textov

class Command(BaseCommand):
    help = 'SMART MAPPER: Mapuje produkty podľa kategórií zdroja, nie podľa názvov.'

    def handle(self, *args, **kwargs):
        self.stdout.write("🧠 SMART MAPPER: Analyzujem pôvodné kategórie...")

        # 1. Získame všetky tvoje kategórie do zoznamu (ciele)
        my_categories = {c.name: c for c in Category.objects.filter(is_active=True)}
        my_category_names = list(my_categories.keys())

        # 2. Získame unikátne "cudzie" kategórie z produktov
        # (Napr. z 10 000 produktov je možno len 150 unikátnych kategórií)
        foreign_categories = Product.objects.exclude(original_category_text__isnull=True).exclude(original_category_text="").values_list('original_category_text', flat=True).distinct()

        self.stdout.write(f"🔎 Našiel som {len(foreign_categories)} unikátnych cudzích kategórií.")

        mappings = {}
        
        # 3. Vytvoríme mapu (Cudzí názov -> Tvoj názov)
        for foreign_cat in foreign_categories:
            # Rozbijeme cestu "Elektronika | Mobily | Apple" -> zoberieme len "Mobily" alebo "Apple"
            # Zvyčajne posledná časť je najpresnejšia
            parts = foreign_cat.split('|')
            last_part = parts[-1].strip()
            
            # Skúsime nájsť najlepšiu zhodu v tvojich kategóriách
            # score_cutoff=85 znamená, že zhoda musí byť aspoň 85%
            best_match = process.extractOne(last_part, my_category_names, scorer=fuzz.token_sort_ratio, score_cutoff=80)
            
            if best_match:
                matched_name, score = best_match
                mappings[foreign_cat] = my_categories[matched_name]
                self.stdout.write(f"   ✅ MAPUJEM: '{last_part}' -> '{matched_name}' (Zhoda: {score}%)")
            else:
                # Ak nenájde, môžeme skúsiť predposlednú časť
                if len(parts) > 1:
                    second_last = parts[-2].strip()
                    best_match_2 = process.extractOne(second_last, my_category_names, scorer=fuzz.token_sort_ratio, score_cutoff=85)
                    if best_match_2:
                        matched_name, score = best_match_2
                        mappings[foreign_cat] = my_categories[matched_name]
                        self.stdout.write(f"   ✅ MAPUJEM (Rodič): '{second_last}' -> '{matched_name}'")

        # 4. Aplikujeme mapu na produkty (Hromadný update)
        self.stdout.write("🚀 Aplikujem zmeny na produkty...")
        updated_count = 0
        
        for foreign_key, my_cat_obj in mappings.items():
            # Nájdi všetky produkty s touto starou kategóriou
            qs = Product.objects.filter(original_category_text=foreign_key)
            updated = qs.update(category=my_cat_obj)
            updated_count += updated
            
        self.stdout.write(self.style.SUCCESS(f"🎉 HOTOVO! Pretriedil som {updated_count} produktov pomocou Smart Mappingu."))