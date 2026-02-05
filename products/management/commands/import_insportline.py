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
import uuid # Pridané pre unikátne slugy

class Command(BaseCommand):
    help = 'Import produktov z Dognet XML feedu (Final Production Version)'

    def add_arguments(self, parser):
        parser.add_argument('feed_url', type=str, help='URL adresa XML feedu')

    def handle(self, *args, **kwargs):
        url = kwargs['feed_url']
        DOGNET_PUBLISHER_ID = "26197" 

        self.stdout.write(f"⏳ Sťahujem XML feed do dočasného súboru...")

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
                        if chunk:
                            f.write(chunk)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Chyba pri sťahovaní: {e}"))
            if os.path.exists(raw_file_path):
                os.remove(raw_file_path)
            return

        # 2. Detekcia GZIP
        final_file_path = raw_file_path
        is_gzipped = False
        
        try:
            with open(raw_file_path, 'rb') as f:
                header = f.read(2)
                if header == b'\x1f\x8b':
                    is_gzipped = True

            if is_gzipped:
                self.stdout.write("📦 Detekovaný GZIP archív -> Rozbaľujem...")
                unzipped_file = tempfile.NamedTemporaryFile(delete=False)
                final_file_path = unzipped_file.name
                unzipped_file.close()
                
                with gzip.open(raw_file_path, 'rb') as f_in:
                    with open(final_file_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                os.remove(raw_file_path) 
            else:
                self.stdout.write("📄 Súbor je už rozbalený (XML).")

        except Exception as e:
             self.stdout.write(self.style.ERROR(f"❌ Chyba pri práci so súborom: {e}"))
             return

        self.stdout.write("🚀 Začínam import VŠETKÝCH produktov...")

        count = 0
        # limit = 50  <-- VYPNUTÝ LIMIT, TERAZ IDEME NAOSTRO!
        
        default_cat, _ = Category.objects.get_or_create(slug='nezaradene', defaults={'name': 'Nezaradené'})

        # 3. Import
        try:
            context = ET.iterparse(final_file_path, events=("end",))
            
            for event, elem in context:
                if elem.tag not in ['SHOPITEM', 'item']:
                    continue
                
                # if count >= limit: break # Limit je vypnutý

                try:
                    name = elem.findtext('PRODUCTNAME') or elem.findtext('PRODUCT') or elem.findtext('name')
                    description = elem.findtext('DESCRIPTION') or ""
                    price_str = elem.findtext('PRICE_VAT') or elem.findtext('price')
                    image_url = elem.findtext('IMGURL') or elem.findtext('image')
                    raw_url = elem.findtext('URL') or elem.findtext('link') 
                    category_text = elem.findtext('CATEGORYTEXT') or "Elektronika"
                    
                    # OPRAVA EAN: Orežeme na max 13 znakov
                    ean_raw = elem.findtext('EAN') or ''
                    ean = ean_raw[:13] 
                    
                    if not name or not price_str or not raw_url:
                        elem.clear()
                        continue

                    encoded_url = urllib.parse.quote_plus(raw_url)
                    affiliate_url = f"https://login.dognet.sk/scripts/fc234pi?a_aid={DOGNET_PUBLISHER_ID}&a_bid=default&dest={encoded_url}"

                    price = Decimal(price_str.replace(',', '.').replace(' ', ''))

                    cat_parts = category_text.split('|')
                    cat_name = cat_parts[-1].strip() if cat_parts else "Nezaradené"
                    
                    category, created = Category.objects.get_or_create(
                        slug=slugify(cat_name)[:50],
                        defaults={'name': cat_name, 'parent': default_cat}
                    )

                    # OPRAVA SLUG: Vytvoríme unikátny slug pridaním kúska náhodného kódu
                    # Aby sme predišli chybe "duplicate key value"
                    base_slug = slugify(name)[:40]
                    unique_slug = f"{base_slug}-{str(uuid.uuid4())[:4]}"

                    product, created = Product.objects.get_or_create(
                        name=name,
                        defaults={
                            'slug': unique_slug, # Použijeme unikátny slug
                            'description': description,
                            'price': price,
                            'category': category,
                            'image_url': image_url,
                            'ean': ean 
                        }
                    )

                    Offer.objects.update_or_create(
                        product=product,
                        shop_name="Mobileonline.sk",
                        defaults={
                            'price': price,
                            'url': affiliate_url,
                            'active': True
                        }
                    )
                    
                    # Vypisujeme len každý 100. produkt, aby sme nezahltili konzolu
                    count += 1
                    if count % 100 == 0:
                        self.stdout.write(f"✅ Spracovaných {count} produktov...")

                except Exception as e:
                    # Len tichý výpis chyby, nezastavujeme import
                    self.stdout.write(self.style.WARNING(f"⚠️ Chyba pri produkte: {e}"))
                finally:
                    elem.clear()

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Chyba pri spracovaní XML: {e}"))
        finally:
            if os.path.exists(final_file_path):
                os.remove(final_file_path)

        self.stdout.write(self.style.SUCCESS(f"🎉 Hotovo! Celkovo importovaných {count} produktov."))
        