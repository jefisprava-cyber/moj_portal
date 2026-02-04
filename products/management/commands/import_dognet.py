from django.core.management.base import BaseCommand
import requests
import xml.etree.ElementTree as ET
from products.models import Product, Category, Offer
from django.utils.text import slugify
from decimal import Decimal
import urllib.parse

class Command(BaseCommand):
    help = 'Import produktov z Dognet XML feedu (Mobileonline - Heureka format)'

    def add_arguments(self, parser):
        parser.add_argument('feed_url', type=str, help='URL adresa XML feedu')

    def handle(self, *args, **kwargs):
        url = kwargs['feed_url']
        
        # --- ✏️ TU DOPLŇ TVOJE ÚDAJE ---
        DOGNET_PUBLISHER_ID = "26197"  # Napr. "9234"
        DOGNET_CAMPAIGN_ID = "303c51" # ID pre Mobileonline (z feed URL), alebo skúsime generický redirect
        # -------------------------------
        

        self.stdout.write(f"⏳ Sťahujem XML feed z: {url} ...")

        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Chyba pri sťahovaní: {e}"))
            return

        try:
            tree = ET.parse(response.raw)
            root = tree.getroot()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Chyba pri čítaní XML: {e}"))
            return

        count = 0
        limit = 50 
        
        default_cat, _ = Category.objects.get_or_create(slug='nezaradene', defaults={'name': 'Nezaradené'})

        self.stdout.write("🚀 Začínam import...")

        # Heureka feed má produkty v tagu <SHOPITEM>
        items = root.findall('SHOPITEM')
        if not items:
             items = root.findall('item') # Pre istotu ak by to bol iný formát

        for item in items:
            if count >= limit:
                break

            try:
                # 1. Získanie údajov (Heureka názvy tagov)
                name = item.findtext('PRODUCTNAME') or item.findtext('PRODUCT') or item.findtext('name')
                description = item.findtext('DESCRIPTION') or ""
                price_str = item.findtext('PRICE_VAT') or item.findtext('price')
                image_url = item.findtext('IMGURL') or item.findtext('image')
                raw_url = item.findtext('URL') or item.findtext('link') # Toto je priamy link
                category_text = item.findtext('CATEGORYTEXT') or "Elektronika"
                
                if not name or not price_str or not raw_url:
                    continue

                # --- VYTVORENIE AFFILIATE LINKU ---
                # Formát Dognet redirectu: https://login.dognet.sk/scripts/fc234pi?a_aid=PUBLISHER&a_bid=BANNER&dest=URL
                # Musíme URL zakódovať (napr. / -> %2F)
                encoded_url = urllib.parse.quote_plus(raw_url)
                
                # Toto je magická formulka pre vytvorenie provízneho linku
                # Používame "Deep Link" skript dognetu
                affiliate_url = f"https://login.dognet.sk/scripts/fc234pi?a_aid={26197}&a_bid=default&dest={encoded_url}"

                # ----------------------------------

                price = Decimal(price_str.replace(',', '.').replace(' ', ''))

                # Spracovanie kategórie
                cat_parts = category_text.split('|')
                cat_name = cat_parts[-1].strip() if cat_parts else "Nezaradené"
                
                category, created = Category.objects.get_or_create(
                    slug=slugify(cat_name)[:50],
                    defaults={'name': cat_name, 'parent': default_cat}
                )

                # Uloženie Produktu
                product, created = Product.objects.get_or_create(
                    name=name,
                    defaults={
                        'slug': slugify(name)[:50],
                        'description': description,
                        'price': price,
                        'category': category,
                        'image_url': image_url,
                        'ean': item.findtext('EAN') or '' 
                    }
                )

                # Uloženie Ponuky s AFFILIATE LINKOM
                Offer.objects.update_or_create(
                    product=product,
                    shop_name="Mobileonline.sk",
                    defaults={
                        'price': price,
                        'url': affiliate_url, # <--- Tu ukladáme ten zarábajúci link
                        'active': True
                    }
                )

                action = "✅" if created else "🔄"
                self.stdout.write(f"{action} {name[:40]}...")
                count += 1

            except Exception as e:
                self.stdout.write(self.style.WARNING(f"⚠️ Chyba: {e}"))

        self.stdout.write(self.style.SUCCESS(f"🎉 Hotovo! {count} produktov importovaných."))