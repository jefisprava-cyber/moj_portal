import ssl
import urllib.request
import xml.etree.ElementTree as ET
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from products.models import Product, Category, Offer
from decimal import Decimal

class Command(BaseCommand):
    help = 'Importuje produkty z Dognet XML feedu'

    def handle(self, *args, **options):
        # ==========================================
        # 1. NASTAVENIA (TOTO ZMENÍŠ, KEĎ BUDEŠ MAŤ LINK)
        # ==========================================
        
        # Sem vložíš ten dlhý odkaz z Dognetu
        URL = "SEM_VLOZIS_LINK_KED_TI_HO_SCHVALIA" 
        
        # Meno obchodu (napr. "4Home.sk", "MerkuryMarket", atď.)
        SHOP_NAME = "Meno Obchodu" 
        
        # ==========================================

        if URL == "SEM_VLOZIS_LINK_KED_TI_HO_SCHVALIA":
            self.stdout.write(self.style.WARNING("⚠️ Nemáš nastavený XML link!"))
            self.stdout.write("Tento skript je pripravený. Keď ti Dognet schváli kampaň, vlož link do riadku 16.")
            return

        self.stdout.write(f"⏳ Sťahujem a spracovávam XML z: {SHOP_NAME}...")
        
        # Ignorovanie SSL chýb (častý problém pri sťahovaní feedov)
        context = ssl._create_unverified_context()
        
        try:
            # Sťahovanie a parsovanie XML
            req = urllib.request.Request(URL, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, context=context) as response:
                
                # Streamované parsovanie
                tree = ET.parse(response)
                root = tree.getroot()

                count_created = 0
                count_updated = 0
                
                # Načítame existujúce kategórie do pamäte (zrýchlenie)
                categories_map = {c.name.lower(): c for c in Category.objects.all()}

                self.stdout.write("🚀 Začínam import produktov...")

                # Dognet používa tag <SHOPITEM> pre každý produkt
                for item in root.findall('SHOPITEM'):
                    try:
                        # 1. Získanie dát z XML
                        # Niektoré feedy majú PRODUCTNAME, iné PRODUCT
                        name = item.findtext('PRODUCTNAME') or item.findtext('PRODUCT')
                        description = item.findtext('DESCRIPTION', '')
                        price_str = item.findtext('PRICE_VAT')
                        img_url = item.findtext('IMGURL', '')
                        ean = item.findtext('EAN')
                        manufacturer = item.findtext('MANUFACTURER', 'Neznámy')
                        xml_category_text = item.findtext('CATEGORYTEXT', '')
                        affiliate_url = item.findtext('URL')

                        if not name or not price_str:
                            continue

                        # Konverzia ceny (výmena čiarky za bodku)
                        price = Decimal(price_str.replace(',', '.'))

                        # 2. KATEGÓRIA (Smart logic)
                        category = None
                        # Vezmeme poslednú časť "Nábytok | Sedačky" -> "Sedačky"
                        feed_cat_name = xml_category_text.split('|')[-1].strip() 
                        
                        if feed_cat_name.lower() in categories_map:
                            category = categories_map[feed_cat_name.lower()]
                        else:
                            # Vytvoríme novú kategóriu ak neexistuje
                            if feed_cat_name:
                                category, _ = Category.objects.get_or_create(name=feed_cat_name)
                                categories_map[feed_cat_name.lower()] = category

                        # 3. ULOŽENIE PRODUKTU (Update or Create)
                        # DÔLEŽITÉ: Ukladáme aj 'price' priamo do produktu (pre našu novú optimalizáciu)
                        product, created = Product.objects.update_or_create(
                            name=name,
                            defaults={
                                'description': description[:5000], 
                                'price': price,  # <--- TOTO JE KĽÚČOVÉ PRE RÝCHLOSŤ WEBU
                                'image_url': img_url,
                                'ean': ean,
                                'brand': manufacturer,
                                'category': category,
                                'original_category_text': xml_category_text,
                                'is_oversized': False 
                            }
                        )

                        # 4. ULOŽENIE PONUKY (Aby fungovalo tlačidlo "Do obchodu")
                        Offer.objects.update_or_create(
                            product=product,
                            shop_name=SHOP_NAME,
                            defaults={
                                'price': price,
                                'url': affiliate_url,
                                'active': True
                            }
                        )

                        if created:
                            count_created += 1
                        else:
                            count_updated += 1
                        
                        if (count_created + count_updated) % 50 == 0:
                            self.stdout.write(f" ... spracovaných {count_created + count_updated}")

                    except Exception as e:
                        continue

                self.stdout.write(self.style.SUCCESS(f'✅ HOTOVO!'))
                self.stdout.write(f'🆕 Nové produkty: {count_created}')
                self.stdout.write(f'🔄 Aktualizované: {count_updated}')

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Kritická chyba pri sťahovaní: {e}"))