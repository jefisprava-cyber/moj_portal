from django.core.management.base import BaseCommand
from products.models import Category, Product
from django.utils.text import slugify
import html

class Command(BaseCommand):
    help = 'Opraví rozbité kategórie z importov (zlúči duplicity a vytvorí strom)'

    def handle(self, *args, **kwargs):
        # 1. Nájdi všetky "rozbité" kategórie
        broken_cats = Category.objects.filter(name__contains="['")
        count = broken_cats.count()
        
        self.stdout.write(f"Našiel som {count} kategórií na opravu. Začínam...")

        processed = 0
        
        for bad_cat in broken_cats:
            original_name = bad_cat.name
            
            # 1. Očistenie názvu: odstráni [' a '] a dekóduje &gt; na >
            clean_name = original_name.replace("['", "").replace("']", "").replace("'", "")
            clean_name = html.unescape(clean_name) # Zmení "Autá &gt; Fiat" na "Autá > Fiat"
            
            # 2. Rozdelenie na časti podľa ">" alebo ","
            if '>' in clean_name:
                parts = [p.strip() for p in clean_name.split('>')]
            else:
                parts = [p.strip() for p in clean_name.split(',')]

            # 3. Budovanie správnej štruktúry (Strom)
            current_parent = None
            
            for part_name in parts:
                if not part_name: continue # Preskoč prázdne
                
                slug = slugify(part_name)
                if not slug: slug = "nezaradene"

                # Nájdi alebo vytvor kategóriu v správnej úrovni (podľa rodiča)
                category_obj, created = Category.objects.get_or_create(
                    slug=slug,
                    parent=current_parent,
                    defaults={'name': part_name}
                )
                
                # Posuň sa o úroveň nižšie
                current_parent = category_obj

            # Na konci cyklu je 'current_parent' tá posledná (cieľová) kategória
            target_category = current_parent

            # 4. Presun produktov
            products = bad_cat.products.all()
            if products.exists():
                products.update(category=target_category)

            # 5. Zmazanie starej zlej kategórie
            bad_cat.delete()
            
            processed += 1
            if processed % 50 == 0:
                self.stdout.write(f"Spracovaných {processed}/{count}...")

        # Finálne čistenie prázdnych kategórií
        self.stdout.write("Mažem prázdne kategórie bez produktov a podkategórií...")
        # Toto zmaže len tie najspodnejšie prázdne, aby sme nezmazali rodičov
        Category.objects.filter(products__isnull=True, children__isnull=True).delete()

        self.stdout.write(self.style.SUCCESS(f'HOTOVO! Úspešne opravených {processed} kategórií.'))