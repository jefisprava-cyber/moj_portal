from django.core.management.base import BaseCommand
from products.models import Product
import requests
import xml.etree.ElementTree as ET

class Command(BaseCommand):
    help = 'Importuje dáta z URL alebo vytvorí stabilné testovacie dáta'

    def add_arguments(self, parser):
        parser.add_argument('url', type=str, nargs='?', default=None, help='URL XML feedu')
        parser.add_argument('shop_name', type=str, nargs='?', default='TestShop', help='Názov e-shopu')

    def handle(self, *args, **kwargs):
        url = kwargs['url']
        shop_name = kwargs['shop_name']

        if not url:
            self.stdout.write("Vytváram stabilné testovacie dáta (Elektronika)...")
            self.create_test_data()
            return

        self.stdout.write(f"Sťahujem dáta z: {url}...")
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            root = ET.fromstring(response.content)
            items = root.findall('.//SHOPITEM') or root.findall('SHOPITEM')

            count = 0
            for item in items:
                name = item.findtext('PRODUCTNAME') or item.findtext('PRODUCT')
                price = item.findtext('PRICE_VAT') or item.findtext('PRICE')
                url_p = item.findtext('URL') or ""
                
                if name and price:
                    clean_price = float(price.replace(',', '.').replace(' ', ''))
                    Product.objects.create(
                        name=name[:255],
                        price=clean_price,
                        shop_name=shop_name,
                        url=url_p
                    )
                    count += 1
            self.stdout.write(self.style.SUCCESS(f'Úspešne naimportovaných {count} produktov.'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Chyba: {e}. Skúste spustiť bez URL pre testovacie dáta.'))

    def create_test_data(self):
        # Simulujeme 3 veľké e-shopy s rovnakým tovarom pre test optimalizácie
        produkty = [
            ("iPhone 15", 899.00), ("Samsung S24", 799.00), 
            ("MacBook Air", 1199.00), ("Sony Slúchadlá", 250.00)
        ]
        shopy = [
            ("Alza-Tech", 1.05), # Mierne drahší
            ("Lacne-PC", 0.95),  # Mierne lacnejší
            ("Mall-Market", 1.0) # Stred
        ]
        
        count = 0
        for shop_name, modif in shopy:
            for name, price in produkty:
                Product.objects.create(
                    name=name,
                    price=round(price * modif, 2),
                    shop_name=shop_name,
                    url="https://www.google.com"
                )
                count += 1
        self.stdout.write(self.style.SUCCESS(f'Vytvorených {count} produktov v 3 obchodoch.'))