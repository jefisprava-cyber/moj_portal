import requests
import xml.etree.ElementTree as ET
from django.core.management.base import BaseCommand
from products.models import Category, Product
from django.utils.text import slugify
from django.db import transaction

class Command(BaseCommand):
    help = 'ARCHITEKT v5.0: FULL VERSION - Buduje strom a agresívne zlučuje nábytok.'

    def handle(self, *args, **kwargs):
        self.stdout.write("🏗️  ARCHITEKT: Začínam kompletnú rekonštrukciu webu...")

        # 1. MAPA PREMENOVANIA (Aby to vyzeralo profesionálne)
        # Toto zabezpečí, že hlavné kategórie budú mať pekné názvy
        REMIX_MAP = {
            'Auto-moto': 'Motoristický svet',
            'Dom a záhrada': 'Bývanie a doplnky',
            'Elektronika': 'Technológie a Gadgets',
            'Hobby': 'Voľný čas a Záľuby',
            'Kozmetika a zdravie': 'Zdravie a Vitalita',
            'Oblečenie a móda': 'Fashion a Štýl',
            'Šport': 'Šport a Tréning',
            'Detský tovar': 'Svet detí',
            'Nábytok': 'Interiérový dizajn', # HLAVNÝ CIEĽ PRE NÁBYTOK
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
            # Reset viditeľnosti (všetko skryjeme, aktivuje to až skript 11)
            Category.objects.update(is_active=False)

            # -------------------------------------------------------
            # 2. VÝSTAVBA ŠTANDARDNÉHO STROMU
            # -------------------------------------------------------
            for category in root.findall('.//CATEGORY'):
                full_path_node = category.find('CATEGORY_FULLNAME')
                if full_path_node is None or not full_path_node.text: continue
                
                parts = full_path_node.text.split(' | ')
                if parts and ('Heureka' in parts[0] or parts[0] == ''): 
                    parts = parts[1:]
                
                if not parts: continue

                # Premenovanie root kategórie podľa mapy
                if parts[0] in REMIX_MAP:
                    parts[0] = REMIX_MAP[parts[0]]
                
                # Budovanie cesty
                current_parent = None
                for part in parts:
                    part_name = part.strip()
                    if not part_name: continue

                    slug = slugify(part_name)
                    # Ošetrenie duplicít slugov
                    if current_parent:
                        slug = slugify(f"{current_parent.slug}-{part_name}")[:200]

                    cat, created = Category.objects.get_or_create(
                        name=part_name,
                        parent=current_parent,
                        defaults={'slug': slug, 'is_active': False} 
                    )
                    current_parent = cat

            self.stdout.write("✅ Strom postavený. Teraz idem opravovať duplicity.")

            # -------------------------------------------------------
            # 3. AGRESÍVNE ZJEDNOTENIE NÁBYTKU (THE FIX)
            # -------------------------------------------------------
            
            # A. Vytvoríme/Nájdeme tú JEDNU SPRÁVNU hlavnú kategóriu
            target_furniture, _ = Category.objects.get_or_create(
                name="Interiérový dizajn",
                parent=None,
                defaults={'slug': 'interierovy-dizajn', 'is_active': True}
            )

            # B. Zoznam kategórií na "odstrel" (Presun a vymazanie)
            # Sem píšeme presné názvy kategórií, ktoré robia bordel (importované alebo staré)
            bad_categories_names = [
                "Nábytok a Bývanie",       # Importované z CJ
                "Nábytok",                 # Stará root kategória
                "Kancelária a Nábytok",    # Iný import
                "Dom a záhrada"            # Starý názov
            ]

            # C. Riešenie ROOT duplicít (Hlavné kategórie)
            for bad_name in bad_categories_names:
                # Nájdi všetky root kategórie s týmto názvom (okrem našej cieľovej)
                bad_cats = Category.objects.filter(name__iexact=bad_name, parent=None).exclude(id=target_furniture.id)
                
                for bad_cat in bad_cats:
                    self.stdout.write(f"   🧹 Zlučujem root '{bad_cat.name}' -> 'Interiérový dizajn'")
                    
                    # 1. Presuň všetky podkategórie pod nového rodiča
                    for child in bad_cat.children.all():
                        child.parent = target_furniture
                        child.save()
                    
                    # 2. Presuň všetky priame produkty
                    Product.objects.filter(category=bad_cat).update(category=target_furniture)
                    
                    # 3. Zmaž starú kategóriu
                    bad_cat.delete()

            # D. Riešenie VNORENEJ duplicity (Bývanie a doplnky -> Nábytok)
            # Toto je častý problém Heureka stromu, kde je Nábytok pod Bývaním
            housing_cat = Category.objects.filter(name="Bývanie a doplnky", parent=None).first()
            if housing_cat:
                nested_furniture = Category.objects.filter(name="Nábytok", parent=housing_cat).first()
                if nested_furniture:
                    self.stdout.write("   🧹 Zlučujem vnorenú 'Bývanie -> Nábytok' -> 'Interiérový dizajn'")
                    
                    # Presun podkategórií (Stoly, Stoličky...) z vnorenej do hlavnej
                    for child in nested_furniture.children.all():
                        child.parent = target_furniture
                        child.save()
                    
                    # Presun produktov
                    Product.objects.filter(category=nested_furniture).update(category=target_furniture)
                    
                    # Výmaz
                    nested_furniture.delete()

            # E. Premenovanie cieľovej kategórie na niečo pekné (voliteľné)
            target_furniture.name = "Interiérový dizajn" 
            target_furniture.save()

        self.stdout.write(self.style.SUCCESS("✅ HOTOVO. Nábytok je teraz zjednotený pod 'Interiérový dizajn'."))