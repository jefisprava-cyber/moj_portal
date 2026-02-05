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
    help = 'Import produktov z 4Home (Google Feed Fix)'

    def handle(self, *args, **kwargs):
        # 4Home Google Feed
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
                response.raise_for_status()
                with open(raw_file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=1024*1024):
                        if chunk: f.write(chunk)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Chyba sťahovania: {e}"))
            if os.path.exists(raw_file_path): os.remove(raw_file_path)
            return

        # 2. Rozbalenie (ak treba)
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
        default_cat, _ = Category.objects.get_or_create(slug='nezaradene', defaults={'name': 'Nezaradené'})
        
        # 👇 DEFINÍCIA GOOGLE NAMESPACE 👇
        ns = '{http://base.google.com/ns/1.0}'

        try:
            context = ET.iterparse(final_file_path, events=("end",))
            
            for event, elem in context:
                # Google feed používa 'item', Heureka 'SHOPITEM'
                if elem.tag not in ['SHOPITEM', 'item', 'entry']:
                    continue
                
                try:
                    # 👇 VYLEPŠENÉ HĽADANIE (s Namespace podporou) 👇
                    
                    # 1. Názov
                    name = (elem.findtext('title') or 
                            elem.findtext(f'{ns}title') or 
                            elem.findtext('PRODUCTNAME'))
                    
                    # 2. Cena (Google používa g:price)
                    price_str = (elem.findtext('price') or 
                                 elem.findtext(f'{ns}price') or 
                                 elem.findtext('PRICE_VAT'))
                    
                    # 3. URL
                    raw_url = (elem.findtext('link') or 
                               elem.findtext(f'{ns}link') or 
                               elem.findtext('URL'))
                    
                    # 4. Obrázok
                    image_url = (elem.findtext('image_link') or 
                                 elem.findtext(f'{ns}image_link') or 
                                 elem.findtext('IMGURL'))
                    
                    # 5. Kategória
                    category_text = (elem.findtext('product_type') or 
                                     elem.findtext(f'{ns}product_type') or 
                                     elem.findtext('CATEGORYTEXT') or 
                                     "Dom a záhrada")
                    
                    # 6. EAN (ak existuje)
                    ean_raw = (elem.findtext('gtin') or 
                               elem.findtext(f'{ns}gtin') or 
                               elem.findtext('EAN') or '')

                    # Kontrola povinných polí
                    if not name or not price_str or not raw_url:
                        elem.clear()
                        continue

                    # Čistenie ceny (Google posiela napr. "12.90 EUR")
                    price_clean = price_str.lower().replace('eur', '').replace('€', '').strip()
                    price = Decimal(price_clean.replace(',', '.').replace(' ', ''))

                    # Affiliate link
                    encoded_url = urllib.parse.quote_plus(raw_url)
                    affiliate_url = f"https://login.dognet.sk/scripts/fc234pi?a_aid={DOGNET_PUBLISHER_ID}&a_bid=default&dest={encoded_url}"

                    # Kategória
                    cat_name = category_text.split('|')[-1].split('>')[-1].strip()
                    category, _ = Category.objects.get_or_create(
                        slug=slugify(cat_name)[:50],
                        defaults={'name': cat_name, 'parent': default_cat}
                    )

                    # Uloženie
                    unique_slug = f"{slugify(name)[:150]}-{str(uuid.uuid4())[:4]}"
                    ean = ean_raw[:13]

                    product, created = Product.objects.update_or_create(
                        original_url=raw_url,
                        defaults={
                            'name': name,
                            'slug': unique_slug if created else slugify(name)[:150] + "-" + str(count),
                            'description': elem.findtext('description') or elem.findtext(f'{ns}description') or "",
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
                    if count % 100 == 0:
                        self.stdout.write(f"✅ {SHOP_NAME}: Spracovaných {count}...")

                except Exception: pass
                finally: elem.clear()

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Chyba XML: {e}"))
        finally:
            if os.path.exists(final_file_path): os.remove(final_file_path)
        
        self.stdout.write(self.style.SUCCESS(f"🎉 Hotovo! {SHOP_NAME} importované: {count} ks."))