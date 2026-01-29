from django.core.management.base import BaseCommand
from products.models import Product, Offer, Category
import xml.etree.ElementTree as ET
from decimal import Decimal
from django.utils.text import slugify

class Command(BaseCommand):
    help = 'Importuje produkty z XML feedu (Simulácia Heureka Feedu)'

    def handle(self, *args, **kwargs):
        self.stdout.write("🔄 Začínam import produktov...")

        # 1. KROK: AUTOMATICKÉ VYTVORENIE KATEGÓRIÍ (Ak chýbajú)
        if not Category.objects.exists():
            self.stdout.write("⚠️ Žiadne kategórie nenájdené. Vytváram základné...")
            
            # Hlavná kategória
            elektronika = Category.objects.create(name="Elektronika", slug="elektronika")
            
            # Podkategórie
            Category.objects.create(name="Smartfóny", slug="smartfony", parent=elektronika)
            Category.objects.create(name="Veľké spotrebiče", slug="velke-spotrebice", parent=elektronika)
            Category.objects.create(name="Notebooky", slug="notebooky", parent=elektronika)
            
            self.stdout.write(self.style.SUCCESS("✅ Kategórie vytvorené."))
        else:
            self.stdout.write("ℹ️ Kategórie už existujú, pokračujem...")

        # 2. VZORKA XML DÁT
        xml_data = """
        <SHOP>
            <SHOPITEM>
                <ITEM_ID>ALZA_123</ITEM_ID>
                <PRODUCTNAME>iPhone 15 Pro 128GB Black Titanium</PRODUCTNAME>
                <DESCRIPTION>Mobilný telefón – 6.1" OLED 2556 × 1179, 120Hz, procesor Apple A17 Pro...</DESCRIPTION>
                <URL>https://alza.sk/iphone-15-pro</URL>
                <IMGURL>https://cdn.alza.sk/foto/123.jpg</IMGURL>
                <PRICE_VAT>1149.90</PRICE_VAT>
                <EAN>190199223344</EAN>
                <DELIVERY_DATE>0</DELIVERY_DATE>
            </SHOPITEM>
            <SHOPITEM>
                <ITEM_ID>NAY_555</ITEM_ID>
                <PRODUCTNAME>Samsung Galaxy S24 Ultra 512GB Grey</PRODUCTNAME>
                <DESCRIPTION>Smartfón Samsung Galaxy S24 Ultra s umelou inteligenciou Galaxy AI...</DESCRIPTION>
                <URL>https://nay.sk/samsung-s24</URL>
                <IMGURL>https://nay.sk/foto/555.jpg</IMGURL>
                <PRICE_VAT>1299.00</PRICE_VAT>
                <EAN>880609012345</EAN>
                <DELIVERY_DATE>2</DELIVERY_DATE>
            </SHOPITEM>
            <SHOPITEM>
                <ITEM_ID>DATART_999</ITEM_ID>
                <PRODUCTNAME>Práčka s predným plnením Samsung WW90</PRODUCTNAME>
                <DESCRIPTION>Parná práčka s kapacitou 9 kg, 1400 ot./min, energetická trieda A...</DESCRIPTION>
                <URL>https://datart.sk/pracka-samsung</URL>
                <IMGURL>https://datart.sk/foto/999.jpg</IMGURL>
                <PRICE_VAT>549.00</PRICE_VAT>
                <EAN>880123456789</EAN>
                <DELIVERY_DATE>0</DELIVERY_DATE>
            </SHOPITEM>
             <SHOPITEM>
                <ITEM_ID>ALZA_MAC</ITEM_ID>
                <PRODUCTNAME>MacBook Air M3 13" Vesmírne sivý</PRODUCTNAME>
                <DESCRIPTION>MacBook – Apple M3, 13.6" IPS 2560 × 1664, RAM 8GB...</DESCRIPTION>
                <URL>https://alza.sk/macbook-air</URL>
                <IMGURL>https://cdn.alza.sk/foto/mac.jpg</IMGURL>
                <PRICE_VAT>1299.00</PRICE_VAT>
                <EAN>199999999999</EAN>
                <DELIVERY_DATE>1</DELIVERY_DATE>
            </SHOPITEM>
        </SHOP>
        """

        # 3. PARSOVANIE XML
        root = ET.fromstring(xml_data)
        count_created = 0

        # Načítame si kategórie do pamäte pre rýchlejšie priradenie
        cat_smart = Category.objects.filter(slug='smartfony').first()
        cat_spotrebice = Category.objects.filter(slug='velke-spotrebice').first()
        cat_notebooky = Category.objects.filter(slug='notebooky').first()
        cat_default = Category.objects.get(slug='elektronika')

        for item in root.findall('SHOPITEM'):
            name = item.find('PRODUCTNAME').text
            description = item.find('DESCRIPTION').text
            price = Decimal(item.find('PRICE_VAT').text)
            url = item.find('URL').text
            img = item.find('IMGURL').text
            ean = item.find('EAN').text
            item_id = item.find('ITEM_ID').text
            delivery = int(item.find('DELIVERY_DATE').text)
            
            # --- LOGIKA PRIRADENIA KATEGÓRIE ---
            target_category = cat_default
            if "iPhone" in name or "Samsung Galaxy" in name:
                target_category = cat_smart
            elif "Práčka" in name or "Chladnička" in name:
                target_category = cat_spotrebice
            elif "MacBook" in name or "Asus" in name:
                target_category = cat_notebooky
            
            # --- LOGIKA NADROZMERNÉHO TOVARU ---
            is_oversized = False
            if "Práčka" in name or "Chladnička" in name or "TV" in name:
                is_oversized = True

            # UPDATE ALEBO CREATE PRODUKTU
            product, created = Product.objects.update_or_create(
                ean=ean,
                defaults={
                    'name': name,
                    'description': description,
                    'image_url': img,
                    'category': target_category,
                    'is_oversized': is_oversized
                }
            )

            # URČENIE OBCHODU PODĽA ID
            shop_name = "Neznámy Shop"
            if "ALZA" in item_id: shop_name = "Alza"
            elif "NAY" in item_id: shop_name = "Nay"
            elif "DATART" in item_id: shop_name = "Datart"

            Offer.objects.update_or_create(
                product=product,
                shop_name=shop_name,
                external_item_id=item_id,
                defaults={
                    'price': price,
                    'delivery_days': delivery,
                    'url': url,
                    'active': True
                }
            )

            if created:
                count_created += 1

        self.stdout.write(self.style.SUCCESS(f"✅ Import hotový! Pridané nové produkty: {count_created}"))