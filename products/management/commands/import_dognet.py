from django.core.management.base import BaseCommand
import requests
import xml.etree.ElementTree as ET
from products.models import Product, Category, Offer
from django.utils.text import slugify
from decimal import Decimal
import urllib.parse
import tempfile
import os
import shutil

class Command(BaseCommand):
    help = 'Import produktov z Dognet XML feedu (Memory Safe Version)'

    def add_arguments(self, parser):
        parser.add_argument('feed_url', type=str, help='URL adresa XML feedu')

    def handle(self, *args, **kwargs):
        url = kwargs['feed_url']
        
        # Tvoje Dognet ID
        DOGNET_PUBLISHER_ID = "26197" 

        self.stdout.write(f"⏳ Sťahujem XML feed do dočasného súboru...")

        # Hlavičky ako prehliadač
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Connection': 'keep-alive'
        }

        # 1. KROK: Stiahnutie na disk (šetrí RAM)
        # Vytvoríme dočasný súbor, kam to stiahneme
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            try:
                with requests.get(url, headers=headers, stream=True) as response:
                    response.raise_for_status()
                    # Kopírujeme dáta zo siete rovno na disk po kúskoch
                    shutil.copyfileobj(response.raw, tmp_file)
                temp_file_path = tmp_file.name
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Chyba pri sťahovaní: {e}"))
                if 'tmp_file' in locals():
                     os.remove(tmp_file.name)
                return

        self.stdout.write(f"📦 Súbor stiahnutý na disk: {temp_file_path}")
        self.stdout.write("🚀 Začínam import (Memory Safe Mode)...")

        count = 0
        limit = 50  # Pre test necháme 50, potom môžeš zvýšiť alebo dať preč
        
        default_cat, _ = Category.objects.get_or_create(slug='nezaradene', defaults={'name': 'Nezaradené'})

        # 2. KROK: Iteratívne čítanie (Memory Safe Parsing)
        try:
            # iterparse číta súbor postupne
            context = ET.iterparse(temp_file_path, events=("end",))
            
            for event, elem in context:
                # Zaujímajú nás len tagy SHOPITEM alebo item
                if elem.tag not in ['SHOPITEM', 'item']:
                    continue
                
                if count >= limit:
                    break

                try:
                    name = elem.findtext('PRODUCTNAME') or elem.findtext('PRODUCT') or elem.findtext('name')
                    description = elem.findtext('DESCRIPTION') or ""
                    price_str = elem.findtext('PRICE_VAT') or elem.findtext('price')
                    image_url = elem.findtext('IMGURL') or elem.findtext('image')
                    raw_url = elem.findtext('URL') or elem.findtext('link') 
                    category_text = elem.findtext('CATEGORYTEXT') or "Elektronika"
                    
                    if not name or not price_str or not raw_url:
                        elem.clear()
                        continue

                    # --- PROVÍZNY LINK ---
                    encoded_url = urllib.parse.quote_plus(raw_url)
                    affiliate_url = f"https://login.dognet.sk/scripts/fc234pi?a_aid={DOGNET_PUBLISHER_ID}&a_bid=default&dest={encoded_url}"

                    price = Decimal(price_str.replace(',', '.').replace(' ', ''))

                    cat_parts = category_text.split('|')
                    cat_name = cat_parts[-1].strip() if cat_parts else "Nezaradené"
                    
                    category, created = Category.objects.get_or_create(
                        slug=slugify(cat_name)[:50],
                        defaults={'name': cat_name, 'parent': default_cat}
                    )

                    product, created = Product.objects.get_or_create(
                        name=name,
                        defaults={
                            'slug': slugify(name)[:50],
                            'description': description,
                            'price': price,
                            'category': category,
                            'image_url': image_url,
                            'ean': elem.findtext('EAN') or '' 
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

                    action = "✅" if created else "🔄"
                    self.stdout.write(f"{action} {name[:40]}...")
                    count += 1

                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"⚠️ Chyba item: {e}"))
                finally:
                    # 3. KROK: Uvoľniť RAM po každom produkte
                    elem.clear()

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Chyba pri spracovaní XML: {e}"))
        finally:
            # Upratovanie: zmažeme dočasný súbor
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

        self.stdout.write(self.style.SUCCESS(f"🎉 Hotovo! {count} produktov importovaných."))