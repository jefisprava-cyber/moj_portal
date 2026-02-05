from django.core.management.base import BaseCommand
from products.models import Product, Category
import sys

class Command(BaseCommand):
    help = 'Opraví rozbité názvy kategórií a vytvorí stromovú štruktúru (Safe Slug Version)'

    def handle(self, *args, **kwargs):
        # Aby sa nám lepšie vypisovalo, nastavíme stdout
        stdout = self.stdout

        stdout.write("🧹 Začínam rekonštrukciu kategórií (Verzia 2.0 - Bezpečné slugy)...")

        # Nájde kategórie, ktoré obsahujú ">" (zlé importy)
        messy_categories = Category.objects.filter(name__contains=">")
        
        count = messy_categories.count()
        stdout.write(f"Našiel som {count} rozbitých kategórií. Idem ich opraviť.")

        processed_count = 0
        
        for old_cat in messy_categories:
            # 1. Očistenie názvu: "['Deti > Hračky']" -> "Deti > Hračky"
            raw_name = old_cat.name.replace("['", "").replace("']", "").replace("'", "")
            
            # 2. Rozdelenie: ["Deti", "Hračky"]
            parts = [p.strip() for p in raw_name.split('>')]
            
            # 3. Budovanie stromu
            current_parent = None
            
            for part in parts:
                if not part: continue
                
                # ZMENA: Nehľadáme podľa slugu, ale podľa názvu a rodiča.
                # Slug sa vygeneruje automaticky vďaka metóde save() v models.py
                try:
                    category, created = Category.objects.get_or_create(
                        name=part,
                        parent=current_parent
                    )
                except Exception as e:
                    # Ak nastane chyba (napr. duplicita), skúsime ju nájsť
                    category = Category.objects.filter(name=part, parent=current_parent).first()
                    if not category:
                        stdout.write(self.style.ERROR(f"❌ Chyba pri vytváraní {part}: {e}"))
                        continue

                current_parent = category

            # 4. Presun produktov do tej najhlbšej (poslednej) kategórie
            final_category = current_parent
            
            if final_category and final_category != old_cat:
                products = Product.objects.filter(category=old_cat)
                updated_count = products.update(category=final_category)
                
                # 5. Zmazať starú zlú kategóriu
                old_cat.delete()
                
                processed_count += 1
                if processed_count % 50 == 0:
                    stdout.write(f"   ✅ Uprataných {processed_count} kategórií...")

        stdout.write(self.style.SUCCESS(f"🎉 HOTOVO! Všetky kategórie boli úspešne prebudované."))