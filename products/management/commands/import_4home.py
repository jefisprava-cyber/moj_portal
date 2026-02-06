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
    help = 'Import 4Home (Golden Logic - Robust)'

    def handle(self, *args, **kwargs):
        # 1. NASTAVENIA PRE 4HOME
        url = "https://www.4home.sk/export/google-products.xml"
        SHOP_NAME = "4Home"
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
        created_count = 0
        updated_count = 0
        errors = 0
        # Zmena: Predvolená kategória pre 4Home
        default_cat, _ = Category.objects.get_or_create(slug='dom-a-zahrada', defaults={'name': 'Dom a záhrada'})

        # 4. PARSOVANIE (Univerzálne pre Heureka aj Google formát)
        try:
            context = ET.iterparse(final_file_path, events=("end",))
            
            for event, elem in context:
                # Získame čistý názov tagu
                tag = elem.tag.lower().split('}')[-1]

                # 4Home používa 'item', Insportline 'shopitem'. Berieme oboje.
                if tag not in ['item', 'shopitem', 'entry']:
                    continue
                
                # Načítame dáta do slovníka
                data = {}
                for child in elem:
                    child_tag = child.tag.lower().split('}')[-1]
                    data[child_tag] = child.text

                try:
                    # Hľadáme názov (Google má 'title', Heureka 'productname')
                    name = data.get('title') or data.get('productname') or data.get('name')
                    description = data.get('description') or ""
                    
                    # Cena (Google má 'price', 'g:price')
                    price_str = data.get('price') or data.get('price_vat') or data.get('g:price')
                    
                    # URL a Obrázok
                    raw_url = data.get('link') or data.get('url')
                    image_url = data.get('image_link') or data.get('imgurl') or data.get('image')
                    
                    # Kategória
                    category_text = data.get('product_type') or data.get('categorytext') or data.get('g:product_type')
                    
                    # EAN (gtin)
                    ean_raw = data.get('gtin') or data.get('ean') or ""

                    if not name or not price_str or not raw_url:
                        elem.clear(); continue

                    # Čistenie ceny
                    price_clean = price_str.lower().replace('eur', '').replace('€', '').replace(',', '.').strip()
                    price = Decimal(price_clean)

                    # Spracovanie kategórie
                    if category_text:
                        # 4Home má kategórie oddelené '>', Heureka '|'
                        if '>' in category_text:
                            cat_parts = category_text.split('>')
                        else:
                            cat_parts = category_text.split('|')
                            
                        cat_name = cat_parts[-1].strip()
                        # Fallback ak je názov prázdny
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
                    
                    ean = ean_raw[:13]

                    # LOGIKA UKLADANIA (EAN -> Názov)
                    product = None
                    if ean and len(ean) > 6:
                        product = Product.objects.filter(ean=ean).first()
                    
                    if not product:
                        product = Product.objects.filter(name=name).first()

                    if product:
                        # UPDATE
                        product.price = price
                        product.category = category
                        if not product.ean and ean: product.ean = ean
                        product.save()
                        updated_count += 1
                    else:
                        # CREATE (Bez problémových stĺpcov)
                        unique_slug = f"{slugify(name)[:150]}-{str(uuid.uuid4())[:4]}"
                        product = Product.objects.create(
                            name=name,
                            slug=unique_slug,
                            description=description,
                            price=price,
                            category=category,
                            image_url=image_url,
                            ean=ean
                        )
                        created_count += 1
                    
                    # Ponuka
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
                    if errors == 1: # Vypíšeme len prvú chybu
                        self.stdout.write(self.style.WARNING(f"⚠️ Chyba pri '{name}': {e}"))
                finally:
                    elem.clear()

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Chyba XML: {e}"))
        finally:
            if os.path.exists(final_file_path):
                os.remove(final_file_path)

        self.stdout.write(self.style.SUCCESS(f"🎉 Hotovo! {SHOP_NAME}: {count} (Nové: {created_count}, Upravené: {updated_count}, Chyby: {errors})."))