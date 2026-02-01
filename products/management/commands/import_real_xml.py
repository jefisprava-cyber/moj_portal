from django.core.management.base import BaseCommand
from products.models import Product, Offer, Category, PriceHistory
from django.utils.text import slugify
from django.db.models import Min
import requests
import xml.etree.ElementTree as ET
from datetime import date
from decimal import Decimal

class Command(BaseCommand):
    help = 'Importuje reálne dáta z Heureka XML feedu'

    def handle(self, *args, **kwargs):
        # 1. URL FEEDU
        # V ostrej prevádzke sem dáš linku, napr.: "https://www.alza.sk/export/products.xml"
        FEED_URL = "https://www.example.com/heureka_feed.xml" 
        
        self.stdout.write("📥 Sťahujem XML feed...")

        try:
            tree = ET.parse('feed.xml') # <--- ČÍTAME SÚBOR
            root = tree.getroot()
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR("Súbor feed.xml neexistuje! Spusti najprv generate_xml.py"))
            return

        CURRENT_SHOP_NAME = "Simulovaný E-shop"

        self.stdout.write("🔄 Spracovávam produkty...")
        
        # --- SIMULÁCIA XML DÁT (Aby ti to fungovalo hneď teraz bez linky) ---
        # TOTO v reále vymažeš a odkomentuješ requests.get() nižšie
        xml_data = """
        <SHOP>
            <SHOPITEM>
                <ITEM_ID>12345</ITEM_ID>
                <PRODUCTNAME>Apple iPhone 15 128GB Black</PRODUCTNAME>
                <DESCRIPTION>Skvelý smartfón s A16 Bionic čipom a 48 Mpx fotoaparátom.</DESCRIPTION>
                <URL>https://www.obchod.sk/p/iphone-15</URL>
                <IMGURL>https://store.storeimages.cdn-apple.com/4982/as-images.apple.com/is/iphone-15-black-select-202309</IMGURL>
                <PRICE_VAT>899.90</PRICE_VAT>
                <EAN>1942530987654</EAN>
                <CATEGORYTEXT>Elektronika | Mobily | Smartfóny</CATEGORYTEXT>
                <DELIVERY_DATE>0</DELIVERY_DATE> 
            </SHOPITEM>
            <SHOPITEM>
                <ITEM_ID>99999</ITEM_ID>
                <PRODUCTNAME>Samsung Galaxy S24 256GB</PRODUCTNAME>
                <DESCRIPTION>Novinka s Galaxy AI a špičkovým displejom.</DESCRIPTION>
                <URL>https://www.inyobchod.sk/samsung-s24</URL>
                <IMGURL>https://images.samsung.com/is/image/samsung/p6pim/sk/sm-s921bzkdeue/gallery/sk-galaxy-s24-sm-s921-sm-s921bzkdeue-539303555</IMGURL>
                <PRICE_VAT>849.00</PRICE_VAT>
                <EAN>8806090123456</EAN>
                <CATEGORYTEXT>Elektronika | Mobily | Smartfóny</CATEGORYTEXT>
                <DELIVERY_DATE>2</DELIVERY_DATE> 
            </SHOPITEM>
            <SHOPITEM>
                <ITEM_ID>55555</ITEM_ID>
                <PRODUCTNAME>Sony PlayStation 5 Slim</PRODUCTNAME>
                <DESCRIPTION>Herná konzola novej generácie.</DESCRIPTION>
                <URL>https://www.hry.sk/ps5</URL>
                <IMGURL>https://gmedia.playstation.com/is/image/SIEPDC/ps5-slim-disc-console-image-block-01-en-16nov23?$1600px$</IMGURL>
                <PRICE_VAT>479.90</PRICE_VAT>
                <EAN>711719577000</EAN>
                <CATEGORYTEXT>Elektronika | Herné konzoly</CATEGORYTEXT>
                <DELIVERY_DATE>1</DELIVERY_DATE> 
            </SHOPITEM>
        </SHOP>
        """
        root = ET.fromstring(xml_data)
        
        # V REÁLE POUŽIJEŠ TOTO:
        # response = requests.get(FEED_URL)
        # response.encoding = 'utf-8' # Niekedy treba 'windows-1250'
        # root = ET.fromstring(response.content)
        # -------------------------------------------------------------------
        
        CURRENT_SHOP_NAME = "Testovací E-shop" # Toto si zmeníš podľa toho, čí feed importuješ

        self.stdout.write("🔄 Spracovávam produkty...")

        for item in root.findall('SHOPITEM'):
            name = item.findtext('PRODUCTNAME')
            description = item.findtext('DESCRIPTION', '')
            url = item.findtext('URL')
            img_url = item.findtext('IMGURL')
            price_str = item.findtext('PRICE_VAT')
            ean = item.findtext('EAN')
            category_path = item.findtext('CATEGORYTEXT', 'Nezaradené')
            delivery = item.findtext('DELIVERY_DATE', '0')
            item_id = item.findtext('ITEM_ID')

            if not name or not price_str:
                continue 

            price = Decimal(price_str)

            # 1. SPRACOVANIE KATEGÓRIE
            # Vezmeme text za posledným " | "
            cat_name = category_path.split('|')[-1].strip()
            category, _ = Category.objects.get_or_create(
                name=cat_name,
                defaults={'slug': slugify(cat_name)}
            )

            # 2. HĽADANIE / VYTVORENIE PRODUKTU
            product = None
            # Najprv skúsime nájsť podľa EAN
            if ean:
                product = Product.objects.filter(ean=ean).first()
            
            # Ak nemáme EAN alebo nenašlo, skúsime podľa názvu
            if not product:
                product = Product.objects.filter(name=name).first()

            if not product:
                # Vytvoríme nový produkt
                product = Product.objects.create(
                    name=name,
                    description=description,
                    image_url=img_url,
                    ean=ean,
                    category=category
                )
                self.stdout.write(f"✨ Nový produkt: {name}")
            else:
                # Aktualizujeme existujúci (napr. lepší obrázok)
                if not product.image_url and img_url:
                    product.image_url = img_url
                    product.save()

            # 3. AKTUALIZÁCIA PONUKY (OFFER)
            offer, created = Offer.objects.get_or_create(
                product=product,
                shop_name=CURRENT_SHOP_NAME,
                defaults={
                    'price': price,
                    'url': url,
                    'delivery_days': int(delivery),
                    'external_item_id': item_id
                }
            )

            if not created:
                if offer.price != price:
                    self.stdout.write(f"📉 Zmena ceny {product.name}: {offer.price} -> {price}")
                    offer.price = price
                    offer.url = url
                    offer.save()
            
            # 4. HISTÓRIA CIEN PRE GRAF
            today = date.today()
            history_exists = PriceHistory.objects.filter(product=product, date=today).exists()
            
            if not history_exists:
                aggs = product.offers.aggregate(min_p=Min('price'))
                min_p = aggs['min_p']
                
                if min_p:
                    # V reále by si avg_p počítal ako priemer všetkých offerov
                    # Teraz pre simuláciu dáme +10%
                    avg_p = min_p * Decimal('1.1')
                    
                    PriceHistory.objects.create(
                        product=product,
                        min_price=min_p,
                        avg_price=avg_p,
                        date=today
                    )

        self.stdout.write(self.style.SUCCESS("✅ Import dokončený!"))