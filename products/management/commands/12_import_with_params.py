import xml.etree.ElementTree as ET
import requests
from django.core.management.base import BaseCommand
from products.models import Product, Category, ProductParameter
from django.utils.text import slugify

class Command(BaseCommand):
    help = 'Importuje produkty AJ s parametrami (pre filtre).'

    def handle(self, *args, **kwargs):
        self.stdout.write("🚀 Začínam import produktov s parametrami...")
        
        # URL tvojho dodávateľa (alebo lokálny súbor)
        URL = "https://www.heureka.sk/direct/xml-export/shops/heureka-sec.xml" # Zmeň na realny feed produktov!
        # Pozor: Heureka sekcie XML neobsahuje produkty. Potrebuješ feed od dodávateľa.
        # Ak len testuješ, musíš mať XML, kde sú tagy <PARAM>
        
        # Tu by si mal použiť tvoj reálny feed (napr. od dodávateľa)
        # Pre ukážku predpokladajme, že sťahujeme feed produktov
        # response = requests.get(YOUR_SUPPLIER_FEED_URL)
        # root = ET.fromstring(response.content)

        # UKÁŽKA LOGIKY (Vlož toto do tvojho hlavného importu):
        """
        for item in root.findall('SHOPITEM'):
            name = item.find('PRODUCTNAME').text
            # ... (vytvorenie produktu ako doteraz) ...
            product = Product.objects.create(...)

            # NOVINKA: Čítanie parametrov
            # Hľadáme všetky tagy <PARAM>
            for param in item.findall('PARAM'):
                p_name = param.find('PARAM_NAME').text
                p_val = param.find('VAL').text
                
                if p_name and p_val:
                    ProductParameter.objects.create(
                        product=product,
                        name=p_name,
                        value=p_val
                    )
        """
        self.stdout.write("ℹ️  Tento skript je len ukážka. Musíš ho integrovať do svojho '00_import_products.py'.")
        self.stdout.write("✅ Princíp: Importér prečíta <PARAM> tagy a uloží ich do tabuľky ProductParameter.")