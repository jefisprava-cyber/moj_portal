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
    help = 'Import produktov z E-spotrebice (Dognet XML)'

    def add_arguments(self, parser):
        parser.add_argument('feed_url', type=str, help='URL adresa XML feedu')

    def handle(self, *args, **kwargs):
        url = kwargs['feed_url']
        # Tvoje ID ostáva rovnaké pre všetky kampane v Dognete
        DOGNET_PUBLISHER_ID = "26197" 

        self.stdout.write(f"⏳ Sťahujem XML feed E-spotrebiče...")

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

        # 2. Detekcia GZIP a rozbalenie
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

        self.stdout.write("🚀 Začínam import E-spotrebiče...")

        count = 0
        
        default_cat, _ = Category.objects.get_or_create(slug='nezaradene', defaults={'name': 'Nezaradené'})

        # 3. Import
        try:
            context = ET.iterparse(final_file_path, events=("end",))
            
            for event, elem in context:
                # E-spotrebice zvyčajne používajú SHOPITEM, ale pre istotu kontrolujeme aj item
                if elem.tag not in ['SHOPITEM', 'item']:
                    continue
                
                try:
                    # Univerzálne hľadanie tagov (Heureka vs Google formát)
                    name = elem.findtext('PRODUCTNAME') or elem.findtext('PRODUCT') or elem.findtext('name') or elem.findtext('title')
                    description = elem.findtext('DESCRIPTION') or elem.findtext('description') or ""
                    price_str = elem.findtext('PRICE_VAT') or elem.findtext('price') or elem.findtext('g:price')
                    image_url = elem.findtext('IMGURL') or elem.findtext('image') or elem.findtext('g:image_link')
                    raw_url = elem.findtext('URL') or elem.findtext('link') or elem.findtext('g:link')
                    category_text = elem.findtext('CATEGORYTEXT') or elem.findtext('category') or "Elektronika"
                    ean_raw = elem.findtext('EAN') or elem.findtext('ean') or ''
                    
                    if not name or not price_str or not raw_url:
                        elem.clear()
                        continue

                    # Čistenie ceny (niekedy tam je " EUR" na konci)
                    price_str = price_str.lower().replace('eur', '').replace('€', '').strip()
                    price = Decimal(price_str.replace(',', '.').replace(' ', ''))

                    # Affiliate link
                    encoded_url = urllib.parse.quote_plus(raw_url)
                    affiliate_url = f"https://login.dognet.sk/scripts/fc234pi?a_aid={DOGNET_PUBLISHER_ID}&a_bid=default&dest={encoded_url}"

                    # Kategória
                    cat_parts = category_text.split('|')
                    cat_name = cat_parts[-1].strip() if cat_parts else "Nezaradené"
                    
                    category, created = Category.objects.get_or_create(
                        slug=slugify(cat_name)[:50],
                        defaults={'name': cat_name, 'parent': default_cat}
                    )

                    # EAN a Slug
                    ean = ean_raw[:13]
                    base_slug = slugify(name)[:40]
                    unique_slug = f"{base_slug}-{str(uuid.uuid4())[:4]}"

                    product, created = Product.objects.get_or_create(
                        name=name,
                        defaults={
                            'slug': unique_slug,
                            'description': description,
                            'price': price,
                            'category': category,
                            'image_url': image_url,
                            'ean': ean 
                        }
                    )

                    # ZMENA: Tu natvrdo dávame názov obchodu E-spotrebiče
                    Offer.objects.update_or_create(
                        product=product,
                        shop_name="E-spotrebiče", 
                        defaults={
                            'price': price,
                            'url': affiliate_url,
                            'active': True
                        }
                    )
                    
                    count += 1
                    if count % 100 == 0:
                        self.stdout.write(f"✅ E-spotrebiče: Spracovaných {count}...")

                except Exception as e:
                    # self.stdout.write(self.style.WARNING(f"⚠️ Chyba: {e}"))
                    pass
                finally:
                    elem.clear()

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Chyba pri spracovaní XML: {e}"))
        finally:
            if os.path.exists(final_file_path):
                os.remove(final_file_path)

        self.stdout.write(self.style.SUCCESS(f"🎉 Hotovo! E-spotrebiče importované: {count} ks."))