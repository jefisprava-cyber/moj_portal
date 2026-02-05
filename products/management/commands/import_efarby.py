from django.core.management.base import BaseCommand
from products.models import Product, Category
import xml.etree.ElementTree as ET
import requests
from django.utils.text import slugify
from decimal import Decimal

class Command(BaseCommand):
    help = 'Import produktov z XML feedu'

    # ==========================================
    # 👇👇👇 TU ZMEŇ URL ADRESU PRE KONKRÉTNY E-SHOP 👇👇👇
    XML_URL = "https://mika.venalio.com/feeds/heureka?websiteLanguageId=1&secretKey=s9ybmxreylrjvtfxr93znxro78e0mscnods8f77d&tagLinks=0"
    # ==========================================

    def handle(self, *args, **kwargs):
        self.stdout.write(f"Sťahujem XML feed z: {self.XML_URL}...")
        
        response = requests.get(self.XML_URL, stream=True)
        if response.status_code != 200:
            self.stdout.write(self.style.ERROR('Chyba pri sťahovaní feedu'))
            return

        tree = ET.parse(response.raw)
        root = tree.getroot()

        count = 0
        # Univerzálny parser pre Heureka aj Google formát
        for item in root.findall('shopitem') or root.findall('item'):
            try:
                # 1. Názov (Skúša rôzne tagy)
                name = item.findtext('PRODUCTNAME') or item.findtext('product') or item.findtext('title') or item.findtext('{http://base.google.com/ns/1.0}title')
                if not name: continue

                # 2. Cena
                price_text = item.findtext('PRICE_VAT') or item.findtext('price_vat') or item.findtext('{http://base.google.com/ns/1.0}price')
                if not price_text: continue
                # Očistenie ceny (napr. "12.90 EUR" -> 12.90)
                price = Decimal(price_text.replace('EUR', '').replace('€', '').strip().replace(',', '.'))

                # 3. Popis
                description = item.findtext('DESCRIPTION') or item.findtext('description') or item.findtext('{http://base.google.com/ns/1.0}description') or ""

                # 4. URL
                url = item.findtext('URL') or item.findtext('link') or item.findtext('{http://base.google.com/ns/1.0}link')
                
                # 5. Obrázok
                image_url = item.findtext('IMGURL') or item.findtext('image_link') or item.findtext('{http://base.google.com/ns/1.0}image_link')

                # 6. Kategória
                category_full = item.findtext('CATEGORYTEXT') or item.findtext('category_text') or item.findtext('{http://base.google.com/ns/1.0}product_type')
                
                if category_full:
                    # Uložíme celú cestu, reorganize.py to potom uprace
                    cats = [c.strip() for c in category_full.split('|')]
                    final_cat_name = cats[-1] # Zoberieme poslednú
                    
                    category, _ = Category.objects.get_or_create(name=final_cat_name)
                else:
                    category, _ = Category.objects.get_or_create(name="Nezaradené")

                # ULOŽENIE PRODUKTU
                Product.objects.update_or_create(
                    original_url=url,
                    defaults={
                        'name': name,
                        'slug': slugify(name)[:200] + "-" + str(count), # Unikátny slug
                        'description': description,
                        'price': price,
                        'image_url': image_url,
                        'category': category,
                        'is_active': True
                    }
                )
                
                count += 1
                if count % 100 == 0:
                    self.stdout.write(f"Importovaných {count} produktov...")

            except Exception as e:
                continue

        self.stdout.write(self.style.SUCCESS(f'HOTOVO! Importovaných {count} produktov.'))