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
        # -------------------------------

        self.stdout.write(f"⏳ Sťahujem XML feed z: {url} ...")

        # --- OPRAVA: Pridávame hlavičku, aby sme vyzerali ako prehliadač ---
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        try:
            response = requests.get(url, headers=headers, stream=True)
            response.raise_for_status()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Chyba pri sťahovaní: {e}"))
            return

        try:
            # Skúsime načítať XML
            tree = ET.parse(response.raw)
            root = tree.getroot()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Chyba pri čítaní XML: {e}"))
            # DIAGNOSTIKA: Ak to zlyhá, vypíšeme prvých 200 znakov, aby sme videli, čo server poslal
            self.stdout.write("--- Začiatok odpovede servera ---")
            self.stdout.write(response.text[:200]) 
            self.stdout.write("---------------------------------")
            return

        count = 0
        limit = 50 
        
        default_cat, _ = Category.objects.get_or_create(slug='nezaradene', defaults={'name': 'Nezaradené'})

        self.stdout.write("🚀 Začínam import...")

        # Heureka feed má produkty v tagu <SHOPITEM>
        items = root.findall('SHOPITEM')
        if not items:
             items = root.findall('item') 

        for item in items:
            if count >= limit:
                break

            try:
                # 1. Získanie údajov (Heureka názvy tagov)
                name = item.findtext('PRODUCTNAME') or item.findtext('PRODUCT') or item.findtext('name')
                description = item.findtext('DESCRIPTION') or ""
                price_str = item.findtext('PRICE_VAT') or item.findtext('price')
                image_url = item.findtext('IMGURL') or item.findtext('image')
                raw_url = item.findtext('URL') or item.findtext('link') 
                category_text = item.findtext('CATEGORYTEXT') or "Elektronika"
                
                if not name or not price_str or not raw_url:
                    continue

                # --- VYTVORENIE AFFILIATE LINKU ---
                encoded_url = urllib.parse.quote_plus(raw_url)
                affiliate_url = f"https://login.dognet.sk/scripts/fc234pi?a_aid={DOGNET_PUBLISHER_ID}&a_bid=default&dest={encoded_url}"
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

                # Uloženie Ponuky
                Offer.objects.update_or_create(
                    product=product,
                    shop_name="Mobileonline.sk",
                    defaults={
                        'price': price,
                        'url': affiliate_url,
                        'active': True
                    }
                )

                action = "✅" if created else "🔄"
                self.stdout.write(f"{action} {name[:40]}...")
                count += 1

            except Exception as e:
                self.stdout.write(self.style.WARNING(f"⚠️ Chyba: {e}"))

        self.stdout.write(self.style.SUCCESS(f"🎉 Hotovo! {count} produktov importovaných."))