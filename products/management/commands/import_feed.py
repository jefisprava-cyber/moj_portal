from django.core.management.base import BaseCommand
from products.models import Product, Offer, Category
import xml.etree.ElementTree as ET
from decimal import Decimal

class Command(BaseCommand):
    help = 'Importuje produkty z XML feedu (Simulácia Heureka Feedu)'

    def handle(self, *args, **kwargs):
        self.stdout.write("🔄 Začínam import produktov...")

        # 1. TOTO JE VZORKA REÁLNEHO XML (Akože sme to stiahli z Alzy)
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
                <CATEGORYTEXT>Elektronika | Mobily | Smartfóny</CATEGORYTEXT>
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
                <CATEGORYTEXT>Elektronika | Mobily | Smartfóny</CATEGORYTEXT>
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
                <CATEGORYTEXT>Elektronika | Veľké spotrebiče | Práčky</CATEGORYTEXT>
                <DELIVERY_DATE>0</DELIVERY_DATE>
            </SHOPITEM>
        </SHOP>
        """

        # 2. PARSOVANIE XML
        root = ET.fromstring(xml_data)

        # Načítame si kategórie z databázy, aby sme vedeli priraďovať
        # Pre test priradíme všetko do "Smartfóny" alebo prvej kategórie, čo nájdeme
        default_category = Category.objects.first()
        if not default_category:
            self.stdout.write(self.style.ERROR("❌ Chyba: Nemáš žiadne kategórie! Vytvor najprv kategórie."))
            return

        count_created = 0
        count_updated = 0

        for item in root.findall('SHOPITEM'):
            # Vytiahneme dáta z XML
            name = item.find('PRODUCTNAME').text
            description = item.find('DESCRIPTION').text
            price = Decimal(item.find('PRICE_VAT').text)
            url = item.find('URL').text
            img = item.find('IMGURL').text
            ean = item.find('EAN').text
            item_id = item.find('ITEM_ID').text
            delivery = int(item.find('DELIVERY_DATE').text)
            
            # --- LOGIKA KATEGÓRIÍ (Zjednodušená) ---
            # Skúsime nájsť kategóriu podľa názvu produktu
            actual_category = default_category
            if "iPhone" in name or "Samsung" in name:
                cat = Category.objects.filter(slug='smartfony').first()
                if cat: actual_category = cat
            
            # --- LOGIKA NADROZMERNÉHO TOVARU ---
            is_oversized = False
            if "Práčka" in name or "Chladnička" in name or "TV" in name:
                is_oversized = True
                self.stdout.write(f"   🚚 Detekovaný nadrozmerný tovar: {name}")

            # 1. KROK: UPDATE ALEBO CREATE PRODUKTU (Podľa EAN)
            product, created = Product.objects.update_or_create(
                ean=ean,
                defaults={
                    'name': name,
                    'description': description,
                    'image_url': img,
                    'category': actual_category,
                    'is_oversized': is_oversized
                }
            )

            # 2. KROK: VYTVORENIE PONUKY (OFFER)
            # Simulujeme, že obchod je "Alza" alebo "Nay" podľa IDčka
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
                self.stdout.write(self.style.SUCCESS(f"✅ Nový produkt: {name} ({shop_name})"))
                count_created += 1
            else:
                self.stdout.write(f"🔄 Aktualizovaný: {name} ({shop_name})")
                count_updated += 1

        self.stdout.write(self.style.SUCCESS(f"--- HOTOVO ---"))
        self.stdout.write(f"Vytvorené: {count_created}")
        self.stdout.write(f"Aktualizované: {count_updated}")