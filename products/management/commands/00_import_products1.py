import ssl
import urllib.request
import xml.etree.ElementTree as ET
import requests
import json
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from products.models import Product, Category, Offer, ProductParameter # Pridaný import ProductParameter
from django.db import transaction # Pridaný import transaction

# ==========================================
# 🎛️ HLAVNÉ VYPÍNAČE
# ==========================================
RUN_XML_IMPORT = False   # ❌ VYPNUTÉ (Dognet už máš, nestrácame čas)
RUN_CJ_IMPORT = True     # ✅ ZAPNUTÉ (Stiahneme Allegro, Asko...)

# ==========================================
# ⚙️ NASTAVENIA LIMITOV
# ==========================================
LIMIT_XML_PRODUCTS = 2000
LIMIT_CJ_PRODUCTS = 2000  # Stiahneme 2000 produktov z každého CJ obchodu

# ==========================================
# 1. KONFIGURÁCIA XML FEEDOV (Teraz sa nepoužijú)
# ==========================================
XML_FEEDS = [
    {"name": "Mobilonline", "url": "https://www.mobilonline.sk/files/comparator/303c51/42/heureka.xml"},
    {"name": "E-spotrebiče", "url": "http://www.e-spotrebice.sk/datafeed/dognet.xml"},
    {"name": "4Home", "url": "https://www.4home.sk/export/google-products.xml"},
    {"name": "Insportline", "url": "https://www.insportline.sk/xml_feed_heureka_new.php"},
    {"name": "Efarby", "url": "https://mika.venalio.com/feeds/heureka?websiteLanguageId=1&secretKey=s9ybmxreylrjvtfxr93znxro78e0mscnods8f77d&tagLinks=0"},
    {"name": "Protein.sk", "url": "https://www.protein.sk/feed/heureka.xml"},
    {"name": "Dizajnove Doplnky", "url": "https://www.dizajnove-doplnky.sk/heureka.xml"}
]

# ==========================================
# 2. KONFIGURÁCIA CJ + AUTOMATICKÉ KATEGÓRIE
# ==========================================
CJ_CONFIG = {
    "token": "bx7Rpc1lf6uy-3jThfx-W6-Mcw",
    "cid": "7864372",    # Company ID
    "pid": "101646612",  # Web ID
    
    # Pridal som parameter "manual_cat", aby sme vedeli, kam to zaradiť,
    # keďže API nám kategórie odmieta poslať.
    "advertisers": [
        {"name": "Allegro.sk", "id": "7167444", "manual_cat": "Nákupné centrum"},
        {"name": "Gorila.sk", "id": "5284767", "manual_cat": "Knihy a Zábava"},
        {"name": "MojaLekaren.sk", "id": "5154184", "manual_cat": "Zdravie a Lieky"},
        {"name": "KancelarskeStolicky", "id": "5493235", "manual_cat": "Kancelária a Nábytok"},
        {"name": "Nazuby.eu", "id": "4322334", "manual_cat": "Zdravie a Lieky"},
        {"name": "Unizdrav", "id": "5654758", "manual_cat": "Zdravie a Pomôcky"},
        {"name": "Asko Nábytok", "id": "4920522", "manual_cat": "Nábytok a Bývanie"}
    ]
}

class Command(BaseCommand):
    help = 'Hybridný importér - Final Robust Version'

    def handle(self, *args, **options):
        self.stdout.write("--- ZAČÍNAM IMPORT ---")
        
        # 1. XML FEEDY
        if RUN_XML_IMPORT:
            self.stdout.write("\n📡 --- FÁZA 1: XML FEEDY ---")
            for feed in XML_FEEDS:
                try:
                    self.import_xml_feed(feed["url"], feed["name"])
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"❌ Chyba {feed['name']}: {e}"))
        else:
            self.stdout.write("\n⏩ FÁZA 1 (XML) PRESKOČENÁ.")

        # 2. CJ API
        if RUN_CJ_IMPORT:
            self.stdout.write("\n📡 --- FÁZA 2: CJ API (Allegro, Asko...) ---")
            try:
                self.import_cj_products()
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Chyba CJ: {e}"))
        else:
            self.stdout.write("\n⏩ FÁZA 2 (CJ) PRESKOČENÁ.")

        self.stdout.write(self.style.SUCCESS("\n🎉 KONIEC."))


    def import_xml_feed(self, url, shop_name):
        self.stdout.write(f"⏳ Sťahujem XML z: {shop_name}...")
        context = ssl._create_unverified_context()
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        
        try:
            with urllib.request.urlopen(req, context=context) as response:
                try: tree = ET.parse(response)
                except: return
                root = tree.getroot()
                
                count_processed = 0
                categories_map = {c.name.lower(): c for c in Category.objects.all()}
                
                # Default kategória
                default_cat, _ = Category.objects.get_or_create(name="Nezaradené", defaults={'slug': 'nezaradene'})
                
                items = root.findall('.//item')
                if not items: items = root.findall('SHOPITEM')
                
                with transaction.atomic(): # Transakcia pre rýchlosť a bezpečnosť
                    for item in items:
                        if count_processed >= LIMIT_XML_PRODUCTS: break
                        try:
                            # 1. Získanie dát
                            name = item.findtext('PRODUCTNAME') or item.findtext('title')
                            price_str = item.findtext('PRICE_VAT') or item.findtext('PRICE')
                            
                            if not price_str:
                                 for child in item:
                                     if 'price' in child.tag: price_str = child.text
                            
                            if not name or not price_str: continue
                            
                            price_str_clean = price_str.replace(',', '.').replace('EUR', '').replace('€', '').strip()
                            try: price = Decimal(price_str_clean)
                            except: continue

                            # Kategória
                            xml_cat = item.findtext('CATEGORYTEXT', '') or item.findtext('g:product_type', '')
                            if not xml_cat:
                                 for child in item:
                                     if 'product_type' in child.tag: xml_cat = child.text
                            
                            feed_cat_name = xml_cat.split('|')[-1].split('>')[-1].strip() 
                            
                            category = default_cat
                            if feed_cat_name.lower() in categories_map: 
                                category = categories_map[feed_cat_name.lower()]
                            else:
                                if feed_cat_name:
                                    category, _ = Category.objects.get_or_create(name=feed_cat_name, defaults={'slug': slugify(feed_cat_name)[:50]})
                                    categories_map[feed_cat_name.lower()] = category

                            ean = item.findtext('EAN') or item.findtext('g:gtin')
                            img_url = item.findtext('IMGURL', '') or item.findtext('image_link', '')
                            if not img_url:
                                for child in item:
                                    if 'image_link' in child.tag: img_url = child.text

                            url_link = item.findtext('URL') or item.findtext('link') or ""
                            desc = item.findtext('DESCRIPTION', '') or ""

                            # 2. Uloženie / Aktualizácia Produktu
                            product, created = Product.objects.update_or_create(
                                name=name,
                                defaults={
                                    'slug': slugify(f"{shop_name}-{name}-{ean}"[:200]),
                                    'description': desc[:5000], 
                                    'price': price, 
                                    'image_url': img_url, 
                                    'ean': ean, 
                                    'category': category, 
                                    'is_oversized': False,
                                    'original_category_text': xml_cat
                                }
                            )

                            # 3. Ponuka
                            Offer.objects.update_or_create(
                                product=product, shop_name=shop_name,
                                defaults={'price': price, 'url': url_link, 'active': True}
                            )
                            
                            # 4. Parametre (NOVINKA)
                            # Vymažeme staré parametre pre tento produkt
                            product.parameters.all().delete()
                            
                            # Hľadáme <PARAM> tagy
                            # Heureka formát: <PARAM><PARAM_NAME>Farba</PARAM_NAME><VAL>Čierna</VAL></PARAM>
                            params = item.findall('PARAM')
                            if not params: params = item.findall('g:product_detail') # Google formát (zložitejší, ale skúsime)

                            for param in params:
                                p_name = param.findtext('PARAM_NAME')
                                p_val = param.findtext('VAL')
                                
                                if p_name and p_val:
                                    ProductParameter.objects.create(
                                        product=product,
                                        name=p_name.strip()[:99],
                                        value=p_val.strip()[:99]
                                    )

                            count_processed += 1
                        except: continue
                self.stdout.write(self.style.SUCCESS(f'   ✅ {shop_name}: {count_processed} produktov.'))
        except Exception as e:
             self.stdout.write(self.style.ERROR(f"❌ Chyba pri sťahovaní {shop_name}: {e}"))


    def import_cj_products(self):
        cj_url = "https://ads.api.cj.com/query"
        headers = {
            "Authorization": f"Bearer {CJ_CONFIG['token']}",
            "Content-Type": "application/json"
        }
        
        for advertiser in CJ_CONFIG["advertisers"]:
            adv_name = advertiser["name"]
            adv_id = advertiser["id"]
            manual_cat_name = advertiser["manual_cat"] 
            
            self.stdout.write(f"⏳ CJ: Pripájam sa na {adv_name}...")
            
            query = f"""
            {{
              products(companyId: "{CJ_CONFIG['cid']}", limit: {LIMIT_CJ_PRODUCTS}, partnerIds: ["{adv_id}"]) {{
                resultList {{
                  title
                  description
                  price {{ amount, currency }}
                  imageLink
                  linkCode(pid: "{CJ_CONFIG['pid']}") {{ clickUrl }}
                }}
              }}
            }}
            """

            try:
                response = requests.post(cj_url, json={'query': query}, headers=headers)
                
                if response.status_code != 200:
                    self.stdout.write(self.style.ERROR(f"   ❌ HTTP {response.status_code}"))
                    continue

                data = response.json()
                if 'errors' in data:
                     self.stdout.write(self.style.ERROR(f"   ❌ API Chyba: {data['errors'][0]['message']}"))
                     continue
                
                products_list = data.get('data', {}).get('products', {}).get('resultList', [])
                
                if not products_list:
                    self.stdout.write(self.style.WARNING(f"   ⚠️ {adv_name}: 0 produktov (API vrátilo prázdny zoznam)."))
                    continue

                count_cj = 0
                
                category, _ = Category.objects.get_or_create(
                    name=manual_cat_name, 
                    defaults={'slug': slugify(manual_cat_name)}
                )

                with transaction.atomic():
                    for item in products_list:
                        try:
                            name = item.get('title')
                            price_val = Decimal(item.get('price', {}).get('amount', 0))
                            currency = item.get('price', {}).get('currency')
                            if currency != 'EUR': continue

                            product, created = Product.objects.update_or_create(
                                name=name,
                                defaults={
                                    'slug': slugify(f"cj-{adv_name}-{name}"[:200]), 
                                    'description': item.get('description', '')[:5000],
                                    'price': price_val,
                                    'image_url': item.get('imageLink', ''),
                                    'category': category, 
                                    'is_oversized': False
                                }
                            )
                            
                            Offer.objects.update_or_create(
                                product=product,
                                shop_name=adv_name,
                                defaults={'price': price_val, 'url': item.get('linkCode', {}).get('clickUrl', ''), 'active': True}
                            )
                            # CJ API bohužiaľ neposiela parametre v tomto základnom query, 
                            # takže tu parametre neimportujeme (zatiaľ).
                            
                            count_cj += 1
                        except: continue

                self.stdout.write(self.style.SUCCESS(f"   ✅ {adv_name}: {count_cj} produktov (Kategória: {manual_cat_name})."))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"   ❌ Chyba {adv_name}: {e}"))