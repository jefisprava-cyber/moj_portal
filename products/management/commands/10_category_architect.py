import requests
import xml.etree.ElementTree as ET
from django.core.management.base import BaseCommand
from products.models import Category, Product
from django.utils.text import slugify
from django.db import transaction

class Command(BaseCommand):
    help = 'ARCHITEKT v6.0 (CLEANER): Zmaže duplicity, zachráni produkty a postaví čistý strom.'

    def handle(self, *args, **kwargs):
        self.stdout.write("🏗️  ARCHITEKT: Začínam rekonštrukciu webu...")

        # -------------------------------------------------------
        # 0. NUKLEÁRNE ČISTENIE (Oprava duplicít)
        # -------------------------------------------------------
        self.stdout.write("🧹 KROK 1: Čistím staré a duplicitné kategórie...")
        
        # Vytvoríme záchrannú kategóriu
        safe_cat, _ = Category.objects.get_or_create(
            name="NEZARADENÉ", 
            slug="nezaradene-temp",
            defaults={'is_active': False}
        )

        # Presunieme tam VŠETKY produkty (aby sa nezmazali s kategóriami)
        count = Product.objects.exclude(category=safe_cat).update(category=safe_cat)
        self.stdout.write(f"   📦 {count} produktov presunutých do bezpečia (NEZARADENÉ).")

        # Zmažeme všetko okrem záchrannej kategórie
        deleted, _ = Category.objects.exclude(id=safe_cat.id).delete()
        self.stdout.write(f"   🗑️  Zmazaných {deleted} starých kategórií (vrátane duplicít).")

        # -------------------------------------------------------
        # 1. PRÍPRAVA MAPY PREMENOVANIA
        # -------------------------------------------------------
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
            self.stdout.write("🌍 Sťahujem definíciu nového stromu...")
            response = requests.get(url)
            response.encoding = 'utf-8'
            root = ET.fromstring(response.content)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Chyba pripojenia: {e}"))
            return

        with transaction.atomic():
            # -------------------------------------------------------
            # 2. VÝSTAVBA NOVÉHO STROMU
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

                    # Hľadáme existujúcu alebo vytvoríme novú
                    cat = Category.objects.filter(name=part_name, parent=current_parent).first()
                    
                    if not cat:
                        base_slug = slugify(part_name)
                        if current_parent:
                            base_slug = slugify(f"{current_parent.slug}-{part_name}")[:200]
                        
                        slug = base_slug
                        counter = 1
                        while Category.objects.filter(slug=slug).exists():
                            slug = f"{base_slug}-{counter}"
                            counter += 1
                        
                        cat = Category.objects.create(
                            name=part_name,
                            parent=current_parent,
                            slug=slug,
                            is_active=False
                        )
                    
                    current_parent = cat

            self.stdout.write("✅ Strom postavený. Teraz idem zlučovať nábytok.")

            # -------------------------------------------------------
            # 3. ZJEDNOTENIE NÁBYTKU
            # -------------------------------------------------------
            target_slug = 'interierovy-dizajn'
            target_furniture = Category.objects.filter(slug=target_slug).first()
            
            # Ak náhodou neexistuje (napr. chyba v Heureka feede), vytvoríme ho
            if not target_furniture:
                 target_furniture = Category.objects.create(
                    name="Interiérový dizajn",
                    parent=None,
                    slug=target_slug,
                    is_active=False
                )

            bad_categories_names = ["Nábytok a Bývanie", "Nábytok", "Kancelária a Nábytok", "Dom a záhrada"]

            for bad_name in bad_categories_names:
                bad_cats = Category.objects.filter(name__iexact=bad_name, parent=None).exclude(id=target_furniture.id)
                for bad_cat in bad_cats:
                    for child in bad_cat.children.all():
                        child.parent = target_furniture
                        child.save()
                    # Presun produktov
                    Product.objects.filter(category=bad_cat).update(category=target_furniture)
                    bad_cat.delete()
            
            # Premenovanie na pekný názov
            target_furniture.name = "Interiérový dizajn"
            target_furniture.save()

        self.stdout.write(self.style.SUCCESS("✅ HOTOVO. Starý bordel je preč, nový strom stojí."))