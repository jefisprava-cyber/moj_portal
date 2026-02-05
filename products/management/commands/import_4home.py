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
    help = 'Import produktov z 4Home (Heureka verzia s Debugom)'

    def handle(self, *args, **kwargs):
        # 👇 ZMENA: Skúšame Heureka feed, ten býva menej blokovaný
        url = "https://www.4home.sk/export/heureka.xml"
        
        DOGNET_PUBLISHER_ID = "26197" 
        SHOP_NAME = "4Home"

        self.stdout.write(f"⏳ Sťahujem XML feed z {SHOP_NAME}...")

        # Vylepšené maskovanie za bežného používateľa
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Referer': 'https://www.google.com/',
            'Upgrade-Insecure-Requests': '1',
            'Accept-Language': 'sk-SK,sk;q=0.9,cs;q=0.8,en-US;q=0.7,en;q=0.6'
        }

        # 1. Stiahnutie
        raw_file = tempfile.NamedTemporaryFile(delete=False)
        raw_file_path = raw_file.name
        raw_file.close()

        try:
            with requests.get(url, headers=headers, stream=True, timeout=30) as response:
                if response.status_code != 200:
                    self.stdout.write(self.style.ERROR(f"❌ Server vrátil chybu: {response.status_code}"))
                    return
                with open(raw_file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=1024*1024):
                        if chunk: f.write(chunk)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Chyba sťahovania: {e}"))
            if os.path.exists(raw_file_path): os.remove(raw_file_path)
            return

        # 2. Kontrola obsahu (DEBUG)
        # Prečítame prvých 200 znakov, aby sme videli, čo sme stiahli
        try:
            with open(raw_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                head = f.read(200)
                if "<!DOCTYPE html>" in head or "<html" in head:
                    self.stdout.write(self.style.ERROR("⛔ POZOR: Server nás zablokoval a poslal HTML stránku namiesto XML."))
                    self.stdout.write(f"Obsah: {head}...")
                    os.remove(raw_file_path)
                    return
        except Exception: pass

        # 3. GZIP Check a rozbalenie
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

        # 4. Import
        self.stdout.write("🚀 Začínam spracovanie produktov...")
        count = 0
        default_cat, _ = Category.objects.get_or_create(slug='dom-a-zahrada', defaults={'name': 'Dom a záhrada'})

        try:
            context = ET.iterparse(final_file_path, events=("end",))
            for event, elem in context:
                if elem.tag not in ['SHOPITEM', 'item']: continue

                try:
                    # Heureka tagy
                    name = elem.findtext('PRODUCTNAME') or elem.findtext('PRODUCT')
                    description = elem.findtext('DESCRIPTION') or ""
                    price_str = elem.findtext('PRICE_VAT') or elem.findtext('PRICE')
                    image_url = elem.findtext('IMGURL')
                    raw_url = elem.findtext('URL')
                    category_text = elem.findtext('CATEGORYTEXT')
                    
                    if not name or not price_str or not raw_url:
                        elem.clear(); continue

                    encoded_url = urllib.parse.quote_plus(raw_url)
                    affiliate_url = f"https://login.dognet.sk/scripts/fc234pi?a_aid={DOGNET_PUBLISHER_ID}&a_bid=default&dest={encoded_url}"
                    price = Decimal(price_str.replace('EUR', '').replace('€', '').replace(',', '.').replace(' ', '').strip())

                    # Kategória
                    if category_text:
                        cat_name = category_text.split('|')[-1].strip()
                    else:
                        cat_name = "Dom a záhrada"
                        
                    category, _ = Category.objects.get_or_create(slug=slugify(cat_name)[:50], defaults={'name': cat_name, 'parent': default_cat})

                    unique_slug = f"{slugify(name)[:150]}-{str(uuid.uuid4())[:4]}"
                    product, created = Product.objects.update_or_create(
                        original_url=raw_url,
                        defaults={
                            'name': name,
                            'slug': unique_slug if created else slugify(name)[:150] + "-" + str(count),
                            'description': description,
                            'price': price,
                            'category': category,
                            'image_url': image_url,
                            'is_active': True
                        }
                    )
                    
                    Offer.objects.update_or_create(product=product, shop_name=SHOP_NAME, defaults={'price': price, 'url': affiliate_url, 'active': True})
                    
                    count += 1
                    if count % 200 == 0: self.stdout.write(f"✅ {count}...")

                except Exception: pass
                finally: elem.clear()

        except Exception as e: self.stdout.write(self.style.ERROR(f"❌ XML Error: {e}"))
        finally: 
            if os.path.exists(final_file_path): os.remove(final_file_path)
        
        self.stdout.write(self.style.SUCCESS(f"🎉 Hotovo! {count} produktov."))