from django.core.management.base import BaseCommand
import requests
import xml.etree.ElementTree as ET
from products.models import Product, Category, Offer
from django.utils.text import slugify
from decimal import Decimal
import urllib.parse

class Command(BaseCommand):
    help = 'Import produktov z Dognet XML feedu (Mobileonline - Heureka format)'

    def add_arguments(self, parser):
        parser.add_argument('feed_url', type=str, help='URL adresa XML feedu')

    def handle(self, *args, **kwargs):
        url = kwargs['feed_url']
        
        # --- TVOJE ID (UŽ VYPLNENÉ) ---
        DOGNET_PUBLISHER_ID = "26197" 
        # -------------------------------

        self.stdout.write(f"⏳ Sťahujem XML feed z: {url} ...")

        # Kompletné hlavičky ako reálny prehliadač Chrome
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'sk-SK,sk;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br', # Povieme serveru, že chápeme kompresiu
            'Connection': 'keep-alive'
        }

        try:
            # ZMENA: stream=False (stiahneme to naraz, aby sme predišli ChunkedEncodingError)
            response = requests.get(url, headers=headers, stream=False, timeout=30)
            response.raise_for_status()
            
            # Automatické dekódovanie (ak je to gzip)
            response.encoding = response.apparent_encoding 
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Chyba pri sťahovaní: {e}"))
            return

        try:
            # Parsovanie z textu v pamäti (nie zo streamu)
            root = ET.fromstring(response.content)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Chyba pri čítaní XML: {e}"))
            self.stdout.write("--- Začiatok stiahnutých dát (kontrola) ---")
            # Vypíšeme len prvých 200 znakov, aby sme videli, čo sme stiahli
            self.stdout.write(str(response.content[:200])) 
            self.stdout.write("-------------------------------------------")
            return

        count = 0
        limit = 50 
        
        default_cat, _ = Category.objects.get_or_create(slug='nezaradene', defaults={'name': 'Nezaradené'})

        self.stdout.write("🚀 Začínam import...")

        items = root.findall('SHOPITEM')
        if not items:
             items = root.findall('item') 

        for item in items:
            if count >= limit:
                break

            try:
                name = item.findtext('PRODUCTNAME') or item.findtext('PRODUCT') or item.findtext('name')
                description = item.findtext('DESCRIPTION') or ""
                price_str = item.findtext('PRICE_VAT') or item.findtext('price')
                image_url = item.findtext('IMGURL') or item.findtext('image')
                raw_url = item.findtext('URL') or item.findtext('link') 
                category_text = item.findtext('CATEGORYTEXT') or "Elektronika"
                
                if not name or not price_str or not raw_url:
                    continue

                # --- PROVÍZNY LINK ---
                encoded_url = urllib.parse.quote_plus(raw_url)
                affiliate_url = f"https://login.dognet.sk/scripts/fc234pi?a_aid={DOGNET_PUBLISHER_ID}&a_bid=default&dest={encoded_url}"
                # ---------------------

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
                        'ean': item.findtext('EAN') or '' 
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
                self.stdout.write(self.style.WARNING(f"⚠️ Chyba: {e}"))

        self.stdout.write(self.style.SUCCESS(f"🎉 Hotovo! {count} produktov importovaných."))