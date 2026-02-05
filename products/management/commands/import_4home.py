from django.core.management.base import BaseCommand
import requests
import xml.etree.ElementTree as ET
from products.models import Product, Category, Offer
from django.utils.text import slugify
from decimal import Decimal
import urllib.parse
import tempfile
import os
import uuid

class Command(BaseCommand):
    help = 'Import produktov z 4Home (Blind Parser - ignoruje namespaces)'

    def handle(self, *args, **kwargs):
        url = "https://www.4home.sk/export/google-products.xml"
        DOGNET_PUBLISHER_ID = "26197" 
        SHOP_NAME = "4Home"

        self.stdout.write(f"⏳ Sťahujem XML feed {SHOP_NAME}...")

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }

        # 1. Stiahnutie
        raw_file = tempfile.NamedTemporaryFile(delete=False)
        raw_file_path = raw_file.name
        raw_file.close()

        try:
            with requests.get(url, headers=headers, stream=True) as response:
                if response.status_code != 200:
                    self.stdout.write(self.style.ERROR(f"❌ Chyba servera: {response.status_code}"))
                    return
                with open(raw_file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=1024*1024):
                        if chunk: f.write(chunk)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Chyba sťahovania: {e}"))
            return

        self.stdout.write(f"🚀 Začínam import {SHOP_NAME} (Blind Mode)...")
        count = 0
        default_cat, _ = Category.objects.get_or_create(slug='nezaradene', defaults={'name': 'Dom a záhrada'})

        try:
            # Používame iterparse
            context = ET.iterparse(raw_file_path, events=("end",))
            
            for event, elem in context:
                # 1. Získame čistý názov tagu (bez {http://...})
                tag = elem.tag.split('}')[-1].lower()

                # Hľadáme 'item', 'entry' alebo 'shopitem'
                if tag not in ['item', 'entry', 'shopitem']:
                    continue

                # 2. Prejdeme všetky deti tohto itemu a uložíme ich do slovníka
                data = {}
                for child in elem:
                    child_tag = child.tag.split('}')[-1].lower() # Očistíme tag
                    data[child_tag] = child.text

                # 3. Vytiahneme dáta (bez ohľadu na prefixy)
                name = data.get('title') or data.get('productname') or data.get('name')
                description = data.get('description') or ""
                price_str = data.get('price') or data.get('price_vat') or data.get('g:price')
                image_url = data.get('image_link') or data.get('imgurl') or data.get('image')
                raw_url = data.get('link') or data.get('url')
                category_text = data.get('product_type') or data.get('categorytext')

                if not name or not price_str or not raw_url:
                    elem.clear()
                    continue

                try:
                    # Čistenie ceny (napr. "12.90 EUR" -> 12.90)
                    price_clean = price_str.lower().replace('eur', '').replace('€', '').strip()
                    price = Decimal(price_clean.replace(',', '.').replace(' ', ''))

                    # Affiliate link
                    encoded_url = urllib.parse.quote_plus(raw_url)
                    affiliate_url = f"https://login.dognet.sk/scripts/fc234pi?a_aid={DOGNET_PUBLISHER_ID}&a_bid=default&dest={encoded_url}"

                    # Kategória
                    if category_text:
                        cat_name = category_text.split('|')[-1].split('>')[-1].strip()
                        category, _ = Category.objects.get_or_create(
                            slug=slugify(cat_name)[:50],
                            defaults={'name': cat_name, 'parent': default_cat}
                        )
                    else:
                        category = default_cat

                    # Uloženie
                    unique_slug = f"{slugify(name)[:150]}-{str(uuid.uuid4())[:4]}"
                    ean = (data.get('gtin') or data.get('ean') or '')[:13]

                    product, created = Product.objects.update_or_create(
                        original_url=raw_url,
                        defaults={
                            'name': name,
                            'slug': unique_slug if created else slugify(name)[:150] + "-" + str(count),
                            'description': description,
                            'price': price,
                            'category': category,
                            'image_url': image_url,
                            'ean': ean,
                            'is_active': True
                        }
                    )
                    
                    Offer.objects.update_or_create(
                        product=product,
                        shop_name=SHOP_NAME,
                        defaults={'price': price, 'url': affiliate_url, 'active': True}
                    )
                    
                    count += 1
                    if count % 200 == 0:
                        self.stdout.write(f"✅ {count}...")

                except Exception:
                    pass
                
                # Uvoľnenie pamäte
                elem.clear()

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Chyba XML: {e}"))
        finally:
            if os.path.exists(raw_file_path):
                os.remove(raw_file_path)

        self.stdout.write(self.style.SUCCESS(f"🎉 Hotovo! {SHOP_NAME} importované: {count} ks."))