from django.core.management.base import BaseCommand
import requests
import xml.etree.ElementTree as ET
from products.models import Product, Category, Offer
from django.utils.text import slugify
from decimal import Decimal
import urllib.parse
import tempfile
import os

class Command(BaseCommand):
    help = 'Import produktov z Dognet XML feedu (Ultimate Fix)'

    def add_arguments(self, parser):
        parser.add_argument('feed_url', type=str, help='URL adresa XML feedu')

    def handle(self, *args, **kwargs):
        url = kwargs['feed_url']
        DOGNET_PUBLISHER_ID = "26197" 

        self.stdout.write(f"⏳ Sťahujem XML feed do dočasného súboru...")

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }

        # 1. KROK: Stiahnutie a automatické rozbalenie (GZIP)
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            temp_file_path = tmp_file.name
            try:
                with requests.get(url, headers=headers, stream=True) as response:
                    response.raise_for_status()
                    for chunk in response.iter_content(chunk_size=1024*1024):
                        if chunk:
                            tmp_file.write(chunk)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Chyba pri sťahovaní: {e}"))
                os.remove(temp_file_path)
                return

        self.stdout.write(f"📦 Súbor uložený: {temp_file_path}")

        # 2. KROK: "Sanitizácia" - nájdeme začiatok XML
        # Niekedy sú na začiatku súboru neviditeľné znaky (BOM) alebo smetie.
        # Tento blok nájde prvú zátvorku '<' a začne čítať odtiaľ.
        start_offset = 0
        with open(temp_file_path, 'rb') as f:
            chunk = f.read(1024)
            start_offset = chunk.find(b'<')
            if start_offset == -1:
                self.stdout.write(self.style.ERROR("❌ Súbor neobsahuje XML dáta (nenašiel som '<')"))
                # Pre istotu vypíšeme čo sme stiahli
                self.stdout.write(f"Obsah: {chunk[:100]}")
                os.remove(temp_file_path)
                return
            
            self.stdout.write(f"🔧 XML začína na pozícii: {start_offset} (Opravujem hlavičku...)")

        self.stdout.write("🚀 Začínam import...")

        count = 0
        limit = 50 
        
        default_cat, _ = Category.objects.get_or_create(slug='nezaradene', defaults={'name': 'Nezaradené'})

        # 3. KROK: Čítanie
        try:
            # Otvoríme súbor znova, preskočíme smetie na začiatku a parsujeme
            with open(temp_file_path, 'rb') as f:
                f.seek(start_offset) # Skoč presne na prvý znak '<'
                
                context = ET.iterparse(f, events=("end",))
                
                for event, elem in context:
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

                        # Provízny link
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
                        elem.clear()

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Chyba pri spracovaní XML: {e}"))
        finally:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

        self.stdout.write(self.style.SUCCESS(f"🎉 Hotovo! {count} produktov importovaných."))