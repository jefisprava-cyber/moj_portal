from django.core.management.base import BaseCommand
from products.models import Category, Product
from django.utils.text import slugify
import html
import random
import string

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
            
            # 1. Očistenie názvu
            clean_name = original_name.replace("['", "").replace("']", "").replace("'", "")
            clean_name = html.unescape(clean_name) 
            
            # 2. Rozdelenie na časti
            if '>' in clean_name:
                parts = [p.strip() for p in clean_name.split('>')]
            else:
                parts = [p.strip() for p in clean_name.split(',')]

            # 3. Budovanie stromu
            current_parent = None
            
            for part_name in parts:
                if not part_name: continue 
                
                slug = slugify(part_name)
                if not slug: slug = "nezaradene"

                # Skúsime nájsť existujúcu kategóriu v tejto úrovni
                category_obj = Category.objects.filter(slug=slug, parent=current_parent).first()

                if not category_obj:
                    # Ak neexistuje presne táto kombinácia (slug + parent), musíme ju vytvoriť.
                    # ALE POZOR: Slug musí byť globálne unikátny.
                    # Takže ak už existuje slug (hoci inde), musíme ho zmeniť.
                    
                    original_slug = slug
                    counter = 1
                    while Category.objects.filter(slug=slug).exists():
                        slug = f"{original_slug}-{counter}"
                        counter += 1
                        # Poistka proti nekonečnému cyklu
                        if counter > 100:
                            slug = f"{original_slug}-{random.randint(1000, 9999)}"
                            break

                    category_obj = Category.objects.create(
                        name=part_name,
                        slug=slug,
                        parent=current_parent
                    )
                
                # Posuň sa o úroveň nižšie
                current_parent = category_obj

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

        # Finálne čistenie
        self.stdout.write("Mažem prázdne kategórie...")
        Category.objects.filter(products__isnull=True, children__isnull=True).delete()

        self.stdout.write(self.style.SUCCESS(f'HOTOVO! Úspešne opravených {processed} kategórií.'))