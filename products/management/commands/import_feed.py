from django.core.management.base import BaseCommand
from products.models import Product, Offer, Category, Bundle
import xml.etree.ElementTree as ET
from decimal import Decimal
import random

class Command(BaseCommand):
    help = 'Importuje produkty, vytvára konkurenciu a zostavy'

    def handle(self, *args, **kwargs):
        self.stdout.write("🔄 Začínam Smart Import...")

        # 1. KATEGÓRIE
        if not Category.objects.exists():
            elektronika = Category.objects.create(name="Elektronika", slug="elektronika")
            Category.objects.create(name="Smartfóny", slug="smartfony", parent=elektronika)
            Category.objects.create(name="Veľké spotrebiče", slug="velke-spotrebice", parent=elektronika)
            Category.objects.create(name="Notebooky", slug="notebooky", parent=elektronika)
            self.stdout.write("✅ Kategórie vytvorené.")

        # 2. ZÁKLADNÉ PRODUKTY (XML)
        xml_data = """
        <SHOP>
            <SHOPITEM>
                <ITEM_ID>ALZA_123</ITEM_ID>
                <PRODUCTNAME>iPhone 15 Pro 128GB Black Titanium</PRODUCTNAME>
                <DESCRIPTION>Mobilný telefón – 6.1" OLED, A17 Pro...</DESCRIPTION>
                <URL>https://alza.sk/iphone</URL>
                <IMGURL>https://cdn.alza.sk/foto/123.jpg</IMGURL>
                <PRICE_VAT>1149.90</PRICE_VAT>
                <EAN>190199223344</EAN>
                <DELIVERY_DATE>0</DELIVERY_DATE>
            </SHOPITEM>
            <SHOPITEM>
                <ITEM_ID>NAY_555</ITEM_ID>
                <PRODUCTNAME>Samsung Galaxy S24 Ultra 512GB Grey</PRODUCTNAME>
                <DESCRIPTION>Smartfón Samsung Galaxy S24 Ultra...</DESCRIPTION>
                <URL>https://nay.sk/samsung</URL>
                <IMGURL>https://nay.sk/foto/555.jpg</IMGURL>
                <PRICE_VAT>1299.00</PRICE_VAT>
                <EAN>880609012345</EAN>
                <DELIVERY_DATE>2</DELIVERY_DATE>
            </SHOPITEM>
            <SHOPITEM>
                <ITEM_ID>DATART_999</ITEM_ID>
                <PRODUCTNAME>Práčka Samsung WW90</PRODUCTNAME>
                <DESCRIPTION>Parná práčka s kapacitou 9 kg...</DESCRIPTION>
                <URL>https://datart.sk/pracka</URL>
                <IMGURL>https://datart.sk/foto/999.jpg</IMGURL>
                <PRICE_VAT>549.00</PRICE_VAT>
                <EAN>880123456789</EAN>
                <DELIVERY_DATE>0</DELIVERY_DATE>
            </SHOPITEM>
             <SHOPITEM>
                <ITEM_ID>ALZA_MAC</ITEM_ID>
                <PRODUCTNAME>MacBook Air M3 13" Vesmírne sivý</PRODUCTNAME>
                <DESCRIPTION>MacBook – Apple M3, 13.6" IPS...</DESCRIPTION>
                <URL>https://alza.sk/macbook</URL>
                <IMGURL>https://cdn.alza.sk/foto/mac.jpg</IMGURL>
                <PRICE_VAT>1299.00</PRICE_VAT>
                <EAN>199999999999</EAN>
                <DELIVERY_DATE>1</DELIVERY_DATE>
            </SHOPITEM>
        </SHOP>
        """

        root = ET.fromstring(xml_data)
        cat_default = Category.objects.get(slug='elektronika')

        for item in root.findall('SHOPITEM'):
            name = item.find('PRODUCTNAME').text
            price = Decimal(item.find('PRICE_VAT').text)
            item_id = item.find('ITEM_ID').text
            ean = item.find('EAN').text
            
            # Jednoduché priradenie kategórie (pre test)
            if "iPhone" in name: cat = Category.objects.get(slug='smartfony')
            elif "Práčka" in name: cat = Category.objects.get(slug='velke-spotrebice')
            elif "MacBook" in name: cat = Category.objects.get(slug='notebooky')
            else: cat = cat_default

            is_oversized = "Práčka" in name

            product, _ = Product.objects.update_or_create(
                ean=ean,
                defaults={'name': name, 'category': cat, 'is_oversized': is_oversized}
            )

            # Hlavná ponuka (pôvodná)
            shop_name = "Alza" if "ALZA" in item_id else ("Nay" if "NAY" in item_id else "Datart")
            
            Offer.objects.update_or_create(
                product=product,
                shop_name=shop_name,
                external_item_id=item_id,
                defaults={'price': price, 'url': item.find('URL').text, 'active': True}
            )

            # --- 3. VYTVORENIE KONKURENCIE (Simulácia) ---
            # Pridáme ten istý produkt do iných obchodov s inou cenou
            shops = ["Alza", "Nay", "Datart"]
            for competitor in shops:
                if competitor != shop_name:
                    # Náhodne zvýšime alebo znížime cenu o 5-50 EUR
                    diff = Decimal(random.randint(-10, 50))
                    fake_price = price + diff
                    
                    Offer.objects.update_or_create(
                        product=product,
                        shop_name=competitor,
                        external_item_id=f"{competitor}_{ean}", # Fiktívne ID
                        defaults={
                            'price': fake_price, 
                            'url': f"https://{competitor.lower()}.sk/produkt",
                            'active': True
                        }
                    )

        # --- 4. VYTVORENIE ZOSTAVY (BUNDLE) ---
        iphone = Product.objects.filter(name__icontains="iPhone").first()
        macbook = Product.objects.filter(name__icontains="MacBook").first()

        if iphone and macbook:
            bundle, created = Bundle.objects.get_or_create(
                slug="apple-start-pack",
                defaults={
                    'name': "Apple Štartovací Balíček",
                    'description': "Kompletná výbava pre študenta alebo manažéra. iPhone 15 Pro + MacBook Air M3 za najlepšiu cenu na trhu.",
                    # Tu by sme dali URL obrázka balíčka
                }
            )
            bundle.products.add(iphone, macbook)
            self.stdout.write("✅ Zostava 'Apple Štartovací Balíček' vytvorená.")

        self.stdout.write(self.style.SUCCESS("🚀 Hotovo! Dáta sú pripravené na testovanie."))