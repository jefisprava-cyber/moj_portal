import requests
import xml.etree.ElementTree as ET
from django.core.management.base import BaseCommand
from products.models import Category, Product
from django.utils.text import slugify
from django.db import transaction

class Command(BaseCommand):
    help = 'ARCHITEKT v5.1 (FIXED): Buduje strom a bezpečne rieši unikátnosť slugov.'

    def handle(self, *args, **kwargs):
        self.stdout.write("🏗️  ARCHITEKT: Začínam kompletnú rekonštrukciu webu...")

        # 1. MAPA PREMENOVANIA
        REMIX_MAP = {
            'Auto-moto': 'Motoristický svet',
            'Dom a záhrada': 'Bývanie a doplnky',
            'Elektronika': 'Technológie a Gadgets',
            'Hobby': 'Voľný čas a Záľuby',
            'Kozmetika a zdravie': 'Zdravie a Vitalita',
            'Oblečenie a móda': 'Fashion a Štýl',
            'Šport': 'Šport a Tréning',
            'Detský tovar': 'Svet detí',
            'Nábytok': 'Interiérový dizajn',
            'Stavebniny': 'Stavba a Rekonštrukcia',
            'Biela technika': 'Domáce spotrebiče',
            'Filmy, knihy, hry': 'Knihy a Zábava',
            'Chovateľské potreby': 'Chovateľské potreby'
        }

        url = "https://www.heureka.sk/direct/xml-export/shops/heureka-sekce.xml"
        
        try:
            self.stdout.write("🌍 Sťahujem definíciu stromu...")
            response = requests.get(url)
            response.encoding = 'utf-8'
            root = ET.fromstring(response.content)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Chyba pripojenia: {e}"))
            return

        with transaction.atomic():
            # Reset viditeľnosti
            Category.objects.update(is_active=False)

            # -------------------------------------------------------
            # 2. VÝSTAVBA ŠTANDARDNÉHO STROMU (S OPRAVOU SLUGOV)
            # -------------------------------------------------------
            for category in root.findall('.//CATEGORY'):
                full_path_node = category.find('CATEGORY_FULLNAME')
                if full_path_node is None or not full_path_node.text: continue
                
                parts = full_path_node.text.split(' | ')
                if parts and ('Heureka' in parts[0] or parts[0] == ''): 
                    parts = parts[1:]
                
                if not parts: continue

                # Premenovanie root kategórie
                if parts[0] in REMIX_MAP:
                    parts[0] = REMIX_MAP[parts[0]]
                
                # Budovanie cesty
                current_parent = None
                for part in parts:
                    part_name = part.strip()
                    if not part_name: continue

                    # --- OPRAVENÁ LOGIKA: Manuálna kontrola namiesto get_or_create ---
                    # 1. Najprv skúsime nájsť existujúcu kategóriu podľa mena a rodiča
                    cat = Category.objects.filter(name=part_name, parent=current_parent).first()
                    
                    if not cat:
                        # 2. Ak neexistuje, musíme ju vytvoriť, ale so SLUGOM, ktorý je voľný
                        base_slug = slugify(part_name)
                        if current_parent:
                            # Pre podkategórie skúsime pridať slug rodiča pre lepšiu unikátnosť
                            base_slug = slugify(f"{current_parent.slug}-{part_name}")[:200]
                        
                        slug = base_slug
                        counter = 1
                        
                        # Cyklus kontroluje, či je slug voľný v CELEJ tabuľke
                        while Category.objects.filter(slug=slug).exists():
                            slug = f"{base_slug}-{counter}"
                            counter += 1
                        
                        # Teraz bezpečne vytvoríme
                        cat = Category.objects.create(
                            name=part_name,
                            parent=current_parent,
                            slug=slug,
                            is_active=False
                        )
                    
                    current_parent = cat

            self.stdout.write("✅ Strom postavený. Teraz idem zlučovať nábytok.")

            # -------------------------------------------------------
            # 3. AGRESÍVNE ZJEDNOTENIE NÁBYTKU
            # -------------------------------------------------------
            
            target_slug = 'interierovy-dizajn'
            # Check if target exists properly
            target_furniture = Category.objects.filter(slug=target_slug).first()
            if not target_furniture:
                 target_furniture = Category.objects.create(
                    name="Interiérový dizajn",
                    parent=None,
                    slug=target_slug,
                    is_active=True
                )

            bad_categories_names = [
                "Nábytok a Bývanie", "Nábytok", "Kancelária a Nábytok", "Dom a záhrada"
            ]

            for bad_name in bad_categories_names:
                bad_cats = Category.objects.filter(name__iexact=bad_name, parent=None).exclude(id=target_furniture.id)
                for bad_cat in bad_cats:
                    self.stdout.write(f"   🧹 Zlučujem root '{bad_cat.name}' -> 'Interiérový dizajn'")
                    for child in bad_cat.children.all():
                        child.parent = target_furniture
                        child.save()
                    Product.objects.filter(category=bad_cat).update(category=target_furniture)
                    bad_cat.delete()

            housing_cat = Category.objects.filter(name="Bývanie a doplnky", parent=None).first()
            if housing_cat:
                nested_furniture = Category.objects.filter(name="Nábytok", parent=housing_cat).first()
                if nested_furniture:
                    self.stdout.write("   🧹 Zlučujem vnorenú 'Bývanie -> Nábytok' -> 'Interiérový dizajn'")
                    for child in nested_furniture.children.all():
                        child.parent = target_furniture
                        child.save()
                    Product.objects.filter(category=nested_furniture).update(category=target_furniture)
                    nested_furniture.delete()
            
            # Premenovanie na pekný názov
            target_furniture.name = "Interiérový dizajn"
            target_furniture.save()

        self.stdout.write(self.style.SUCCESS("✅ HOTOVO. Architekt dobehol úspešne."))