from django.core.management.base import BaseCommand
import requests
import xml.etree.ElementTree as ET
from products.models import Product, Category, Offer
from django.utils.text import slugify
from decimal import Decimal

class Command(BaseCommand):
    help = 'Import produktov z Dognet XML feedu (Mobileonline)'

    def add_arguments(self, parser):
        parser.add_argument('feed_url', type=str, help='URL adresa XML feedu')

    def handle(self, *args, **kwargs):
        url = kwargs['feed_url']
        self.stdout.write(f"⏳ Sťahujem XML feed z: {url} ...")

        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Chyba pri sťahovaní: {e}"))
            return

        # Spracovanie XML
        try:
            tree = ET.parse(response.raw)
            root = tree.getroot()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Chyba pri čítaní XML: {e}"))
            return

        count = 0
        limit = 50 # NA TEST: Dáme len 50 produktov, aby to nezbehlo dlho
        
        # Vytvoríme "zbernú" kategóriu, ak nevieme kam produkt zaradiť
        default_cat, _ = Category.objects.get_or_create(
            slug='nezaradene', 
            defaults={'name': 'Nezaradené'}
        )

        self.stdout.write("🚀 Začínam import...")

        for item in root.findall('item'): # Dognet zvyčajne používa tag <item>
            if count >= limit:
                break

            try:
                # 1. Získanie údajov z XML (Dognet štandard)
                name = item.findtext('productname') or item.findtext('name')
                description = item.findtext('description') or ""
                price_str = item.findtext('price_vat') or item.findtext('price')
                image_url = item.findtext('imgurl') or item.findtext('image')
                affiliate_url = item.findtext('url') or item.findtext('link')
                category_text = item.findtext('categorytext') or "Elektronika"
                
                if not name or not price_str:
                    continue

                # Konverzia ceny
                price = Decimal(price_str.replace(',', '.').replace(' ', ''))

                # 2. Spracovanie kategórie (jednoduché)
                # Skúsime nájsť kategóriu podľa prvého slova v categorytext
                cat_name = category_text.split('|')[-1].strip() # Zoberieme poslednú časť "Elektronika | Mobily" -> "Mobily"
                category, created = Category.objects.get_or_create(
                    slug=slugify(cat_name),
                    defaults={'name': cat_name, 'parent': default_cat}
                )

                # 3. Uloženie Produktu
                product, created = Product.objects.get_or_create(
                    name=name,
                    defaults={
                        'slug': slugify(name)[:50], # Orezanie slug ak je dlhý
                        'description': description,
                        'price': price,
                        'category': category,
                        'image_url': image_url,
                        # Uložme si ID z feedu ak existuje, aby sme nerobili duplicity
                        'ean': item.findtext('ean') or '' 
                    }
                )

                # 4. Uloženie Ponuky (Offer) - Aby fungovalo tlačidlo "Do obchodu"
                Offer.objects.update_or_create(
                    product=product,
                    shop_name="Mobileonline.sk",
                    defaults={
                        'price': price,
                        'url': affiliate_url,
                        'active': True
                    }
                )

                action = "✅ Vytvorený" if created else "🔄 Aktualizovaný"
                self.stdout.write(f"{action}: {name[:30]}...")
                count += 1

            except Exception as e:
                self.stdout.write(self.style.WARNING(f"⚠️ Chyba pri produkte: {e}"))

        self.stdout.write(self.style.SUCCESS(f"🎉 Import hotový! Spracovaných {count} produktov."))