from django.core.management.base import BaseCommand
from products.models import Category, Product
from django.utils.text import slugify
import re

class Command(BaseCommand):
    help = 'Opraví a zlúči rozbité kategórie z importov'

    def handle(self, *args, **kwargs):
        self.stdout.write("Začínam opravu kategórií...")
        
        # 1. Krok: Oprava názvov s ['... > ...']
        categories = Category.objects.filter(name__contains="['")
        
        for cat in categories:
            original_name = cat.name
            
            # Vyčistenie názvu od zátvoriek a úvodzoviek
            clean_name = original_name.replace("['", "").replace("']", "").replace("'", "")
            
            # Rozdelenie podľa " > " alebo " &gt; "
            parts = re.split(r'\s*>\s*|\s*&gt;\s*', clean_name)
            
            # Berieme poslednú časť ako názov kategórie (napr. "Kancelárske stoličky")
            # Alebo ak je to príliš všeobecné, tak spojíme posledné dve
            final_name = parts[-1].strip()
            
            # Ak je názov len "Ostatné" alebo "Príslušenstvo", skúsime pridať predradenú kategóriu
            if len(parts) > 1 and len(final_name) < 4:
                final_name = f"{parts[-2].strip()} {final_name}"

            self.stdout.write(f"Spracovávam: {original_name} -> {final_name}")

            # Nájdi alebo vytvor správnu kategóriu
            target_category = Category.objects.filter(name__iexact=final_name).first()
            
            if not target_category:
                # Ak neexistuje, vytvoríme ju (alebo premenujeme túto, ak je to jednoduchšie)
                # Tu radšej vytvoríme novú čistú, aby sme mali poriadok
                target_slug = slugify(final_name)
                # Ošetriť unikátnosť slugu
                if Category.objects.filter(slug=target_slug).exists():
                    target_slug = f"{target_slug}-{cat.id}"
                
                target_category = Category.objects.create(name=final_name, slug=target_slug)
                self.stdout.write(f"  --> Vytvorená nová kategória: {final_name}")

            # Presun produktov
            products = Product.objects.filter(category=cat)
            count = products.count()
            
            if count > 0:
                products.update(category=target_category)
                self.stdout.write(f"  --> Presunutých {count} produktov do {target_category.name}")
            
            # Zmazanie starej zlej kategórie
            cat.delete()
            self.stdout.write(f"  --> Stará kategória zmazaná.")

        # 2. Krok: Zmazanie prázdnych kategórií (voliteľné)
        self.stdout.write("Mažem prázdne kategórie...")
        empty_cats = Category.objects.filter(products__isnull=True, children__isnull=True)
        # delete_count = empty_cats.count()
        # empty_cats.delete() # Odkomentuj, ak chceš zmazať úplne prázdne kategórie bez podkategórií
        # self.stdout.write(f"Zmazaných {delete_count} prázdnych kategórií.")

        self.stdout.write(self.style.SUCCESS('Hotovo! Kategórie sú upratané.'))