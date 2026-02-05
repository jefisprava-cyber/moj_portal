from django.core.management.base import BaseCommand
import requests
import xml.etree.ElementTree as ET
from products.models import Product, Category, Offer
from django.utils.text import slugify
from decimal import Decimal
import urllib.parse
import tempfile
import os
import gzip
import shutil
import uuid

class Command(BaseCommand):
    help = 'Import Insportline (Robustný Parser)'

    def handle(self, *args, **kwargs):
        # 1. NASTAVENIA
        url = "https://www.insportline.sk/xml_feed_heureka_new.php"
        SHOP_NAME = "Insportline"
        DOGNET_PUBLISHER_ID = "26197" 

        self.stdout.write(f"⏳ Sťahujem XML feed {SHOP_NAME}...")

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        }

        # 2. STIAHNUTIE
        raw_file = tempfile.NamedTemporaryFile(delete=False)
        raw_file_path = raw_file.name
        raw_file.close()

        try:
            with requests.get(url, headers=headers, stream=True, timeout=60) as response:
                if response.status_code != 200:
                    self.stdout.write(self.style.ERROR(f"❌ Chyba servera: {response.status_code}"))
                    return
                with open(raw_file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=1024*1024):
                        if chunk: f.write(chunk)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Chyba sťahovania: {e}"))
            return

        # 3. GZIP CHECK
        final_file_path = raw_file_path
        try:
            with open(raw_file_path, 'rb') as f:
                if f.read(2) == b'\x1f\x8b':
                    self.stdout.write("📦 Rozbaľujem GZIP...")
                    unzipped = tempfile.NamedTemporaryFile(delete=False)
                    final_file_path = unzipped.name
                    unzipped.close()
                    with gzip.open(raw_file_path, 'rb') as f_in, open(final_file_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                    os.remove(raw_file_path)
        except Exception: pass

        self.stdout.write(f"🚀 Začínam import {SHOP_NAME}...")

        count = 0
        errors = 0
        default_cat, _ = Category.objects.get_or_create(slug='sport', defaults={'name': 'Šport'})

        # 4. PARSOVANIE (Slepý režim - ignoruje case sensitivity)
        try:
            context = ET.iterparse(final_file_path, events=("end",))
            
            for event, elem in context:
                # Získame len názov tagu bez namespace a malými písmenami
                tag = elem.tag.lower().split('}')[-1]

                if tag != 'shopitem':
                    continue
                
                # Načítame všetky pod-tagy do slovníka pre jednoduchší prístup
                data = {}
                for child in elem:
                    child_tag = child.tag.lower().split('}')[-1]
                    data[child_tag] = child.text

                # Teraz bezpečne vyberáme dáta
                try:
                    name = data.get('productname') or data.get('product')
                    description = data.get('description') or ""
                    
                    price_str = data.get('price_vat') or data.get('price')
                    
                    raw_url = data.get('url') or data.get('link')
                    image_url = data.get('imgurl') or data.get('image')
                    category_text = data.get('categorytext')
                    ean_raw = data.get('ean') or ""

                    # Validácia
                    if not name or not price_str or not raw_url:
                        elem.clear()
                        continue

                    # Konverzia ceny (Insportline má "75.9" bez EUR, ale pre istotu čistíme)
                    price_clean = price_str.lower().replace('eur', '').replace('€', '').replace(',', '.').strip()
                    price = Decimal(price_clean)

                    # Kategória
                    if category_text:
                        cat_parts = category_text.split('|')
                        cat_name = cat_parts[-1].strip()
                        if not cat_name and len(cat_parts) > 1: cat_name = cat_parts[-2].strip()
                        
                        category, _ = Category.objects.get_or_create(
                            slug=slugify(cat_name)[:50],
                            defaults={'name': cat_name, 'parent': default_cat}
                        )
                    else:
                        category = default_cat

                    # Affiliate URL
                    encoded_url = urllib.parse.quote_plus(raw_url)
                    affiliate_url = f"https://login.dognet.sk/scripts/fc234pi?a_aid={DOGNET_PUBLISHER_ID}&a_bid=default&dest={encoded_url}"

                    # Uloženie
                    unique_slug = f"{slugify(name)[:150]}-{str(uuid.uuid4())[:4]}"
                    ean = ean_raw[:13]

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

                except Exception as e:
                    errors += 1
                    # Vypíšeme prvú chybu, aby sme vedeli, čo sa deje
                    if errors == 1:
                        self.stdout.write(self.style.WARNING(f"⚠️ Chyba pri spracovaní produktu '{name}': {e}"))
                finally:
                    elem.clear()

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Chyba XML parsera: {e}"))
        finally:
            if os.path.exists(final_file_path):
                os.remove(final_file_path)

        self.stdout.write(self.style.SUCCESS(f"🎉 Hotovo! {SHOP_NAME} importované: {count} ks (Chyby: {errors})."))