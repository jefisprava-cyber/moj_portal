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
    help = 'DEBUG Import Insportline'

    def handle(self, *args, **kwargs):
        # URL FEEDU
        url = "https://www.insportline.sk/xml_feed_heureka_new.php"
        
        self.stdout.write(f"⏳ Sťahujem XML feed Insportline...")

        # VYLEPŠENÉ HLAVIČKY (aby sme vyzerali ako bežný prehliadač)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Referer': 'https://www.google.com/',
        }

        # 1. STIAHNUTIE
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
            return

        # 🛑 DIAGNOSTIKA: Čo sme vlastne stiahli?
        self.stdout.write("\n🔍 --- ZAČIATOK STIAHNUTÉHO SÚBORU ---")
        try:
            with open(raw_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(500) # Prečítame prvých 500 znakov
                self.stdout.write(content)
        except Exception as e:
            self.stdout.write(f"❌ Nedá sa prečítať súbor: {e}")
        self.stdout.write("\n🔍 --- KONIEC UKÁŽKY ---\n")

        # 2. GZIP CHECK
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

        # 3. Import (Ak je súbor v poriadku)
        self.stdout.write("🚀 Začínam import...")
        count = 0
        default_cat, _ = Category.objects.get_or_create(slug='sport', defaults={'name': 'Šport'})
        DOGNET_PUBLISHER_ID = "26197" 

        try:
            context = ET.iterparse(final_file_path, events=("end",))
            for event, elem in context:
                if elem.tag != 'SHOPITEM': continue
                
                try:
                    name = elem.findtext('PRODUCTNAME') or elem.findtext('PRODUCT')
                    price_str = elem.findtext('PRICE_VAT')
                    raw_url = elem.findtext('URL')
                    
                    if not name or not price_str or not raw_url: continue

                    price = Decimal(price_str.replace('EUR', '').replace('€', '').replace(',', '.').strip())
                    
                    # Rýchle uloženie pre test
                    unique_slug = f"{slugify(name)[:100]}-{str(uuid.uuid4())[:4]}"
                    prod, _ = Product.objects.get_or_create(
                        original_url=raw_url,
                        defaults={'name': name, 'slug': unique_slug, 'price': price, 'category': default_cat, 'is_active': True}
                    )
                    Offer.objects.get_or_create(product=prod, shop_name="Insportline", defaults={'price': price, 'url': raw_url, 'active': True})
                    
                    count += 1
                    if count % 100 == 0: self.stdout.write(f"✅ {count}...")

                except Exception: pass
                finally: elem.clear()

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Chyba XML: {e}"))
        finally:
            if os.path.exists(final_file_path): os.remove(final_file_path)
        
        self.stdout.write(self.style.SUCCESS(f"🎉 Hotovo! Importovaných: {count}"))