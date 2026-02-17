import ssl
import urllib.request
import xml.etree.ElementTree as ET
import requests
import json
import time
import gc
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from products.models import Product, Category, Offer, ProductParameter
from django.db import transaction

# ==========================================
# 🎛️ HLAVNÉ VYPÍNAČE A LIMITY (TEST MODE)
# ==========================================
RUN_XML_IMPORT = True    # XML Feedy
RUN_CJ_IMPORT = True     # CJ API (Allegro, Asko...)

# ⚠️ LIMITY (Nastavené na 500 pre rýchly test, pre ostrú prevádzku zvýš na 15000)
LIMIT_PER_CJ_ADVERTISER = 2000    
LIMIT_XML_PRODUCTS = 2000         
BATCH_SIZE_CJ = 500              

# ==========================================
# 1. KONFIGURÁCIA XML FEEDOV
# ==========================================
XML_FEEDS = [
    {"name": "Mobilonline", "url": "https://www.mobilonline.sk/files/comparator/303c51/42/heureka.xml"},
    {"name": "E-spotrebiče", "url": "http://www.e-spotrebice.sk/datafeed/dognet.xml"},
    {"name": "4Home", "url": "https://www.4home.sk/export/google-products.xml"},
    {"name": "Insportline", "url": "https://www.insportline.sk/xml_feed_heureka_new.php"},
    {"name": "Efarby", "url": "https://mika.venalio.com/feeds/heureka?websiteLanguageId=1&secretKey=s9ybmxreylrjvtfxr93znxro78e0mscnods8f77d&tagLinks=0"},
    {"name": "Protein.sk", "url": "https://www.protein.sk/feed/heureka.xml"},
    {"name": "Dizajnove Doplnky", "url": "https://www.dizajnove-doplnky.sk/heureka.xml"},
    {"name": "Svet-svietidiel.sk", "url": "https://feeds.mergado.com/svet-svietidiel-sk-heureka-sk-2-f5937a18cc9c2f1e6dec0b725e85ef87.xml"}
]

# ==========================================
# 2. KONFIGURÁCIA CJ (Allegro, Asko...)
# ==========================================
CJ_CONFIG = {
    "token": "O2uledg8fW-ArSOgXxt2jEBB0Q", 
    "cid": "7864372",    # Company ID
    "pid": "101646612",  # Web ID
    
    # manual_cat tu slúži UŽ LEN ako textová pomôcka pre Sorter (nebude to názov kategórie v DB)
    "advertisers": [
        {"name": "Allegro.sk", "id": "7167444", "manual_cat": "Nákupné centrum"},
        {"name": "Gorila.sk", "id": "5284767", "manual_cat": "Knihy a Zábava"},
        {"name": "MojaLekaren.sk", "id": "5154184", "manual_cat": "Zdravie a Lieky"},
        {"name": "KancelarskeStolicky", "id": "5493235", "manual_cat": "Kancelária a Nábytok"},
        {"name": "Nazuby.eu", "id": "4322334", "manual_cat": "Zdravie a Lieky"},
        {"name": "Asko Nábytok", "id": "4920522", "manual_cat": "Nábytok a Bývanie"},
        {"name": "Raj hračiek", "id": "7260722", "manual_cat": "Hračky a deti"},
        {"name": "Roboticky-vysavac", "id": "5352874", "manual_cat": "Domáce spotrebiče"},
        {"name": "XXXLutz", "id": "5547578", "manual_cat": "Nábytok a Bývanie"}
    ]
}

class Command(BaseCommand):
    help = 'Univerzálny Importér - VŠETKO DO NEZARADENÉ'

    def handle(self, *args, **options):
        self.stdout.write("🚀 ŠTARTUJEM IMPORT (Cieľ: Jedna kategória NEZARADENÉ)...")
        
        # --- VYTVORENIE JEDNEJ SPOLOČNEJ KATEGÓRIE ---
        # is_active=False znamená, že bordel nebude vidieť na webe, kým ho neroztriediš.
        self.fallback_cat, _ = Category.objects.get_or_create(
            name="NEZARADENÉ (IMPORT)", 
            defaults={'slug': 'nezaradene-import', 'is_active': False}
        )
        self.stdout.write(f"📦 Všetky produkty pôjdu do: {self.fallback_cat.name}")

        # 1. XML FEEDY
        if RUN_XML_IMPORT:
            self.stdout.write("\n📡 --- FÁZA 1: XML FEEDY ---")
            for feed in XML_FEEDS:
                try:
                    self.import_xml_feed(feed["url"], feed["name"])
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"❌ Chyba {feed['name']}: {e}"))
                gc.collect() 
        
        # 2. CJ API
        if RUN_CJ_IMPORT:
            self.stdout.write("\n📡 --- FÁZA 2: CJ API ---")
            self.import_cj_products()
        
        self.stdout.write(self.style.SUCCESS("\n🎉 IMPORT DOKONČENÝ."))


    def import_xml_feed(self, url, shop_name):
        self.stdout.write(f"⏳ XML: Sťahujem {shop_name}...")
        context = ssl._create_unverified_context()
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        
        try:
            with urllib.request.urlopen(req, context=context) as response:
                try: tree = ET.parse(response)
                except: return

                root = tree.getroot()
                items = root.findall('.//item') or root.findall('.//SHOPITEM') or root.findall('channel/item')
                
                count = 0
                with transaction.atomic():
                    for item in items:
                        if count >= LIMIT_XML_PRODUCTS: break
                        try:
                            name = item.findtext('PRODUCTNAME') or item.findtext('title') or item.findtext('g:title')
                            price_str = item.findtext('PRICE_VAT') or item.findtext('PRICE') or item.findtext('g:price')
                            
                            if not price_str:
                                for child in item:
                                    if 'price' in child.tag: price_str = child.text

                            if not name or not price_str: continue
                            
                            price_str_clean = price_str.replace(',', '.').replace('EUR', '').replace('€', '').strip()
                            try: price = Decimal(price_str_clean)
                            except: continue

                            xml_cat = item.findtext('CATEGORYTEXT', '') or item.findtext('g:product_type', '')
                            clean_cat = xml_cat.replace('|', '>').split('>')[-1].strip()
                            
                            ean = item.findtext('EAN') or item.findtext('g:gtin')
                            img_url = item.findtext('IMGURL', '') or item.findtext('image_link', '') or item.findtext('g:image_link', '')
                            url_link = item.findtext('URL') or item.findtext('link') or item.findtext('g:link') or ""
                            desc = item.findtext('DESCRIPTION', '') or item.findtext('description', '') or ""

                            product, _ = Product.objects.update_or_create(
                                name=name[:255],
                                defaults={
                                    'slug': slugify(f"{shop_name}-{name}-{ean}"[:200]),
                                    'description': desc[:5000], 
                                    'price': price, 
                                    'image_url': img_url, 
                                    'ean': ean[:13] if ean else None, 
                                    'category': self.fallback_cat,  # <--- VŠETKO SEM
                                    'is_oversized': False,
                                    'original_category_text': xml_cat[:499] if xml_cat else clean_cat[:499]
                                }
                            )

                            Offer.objects.update_or_create(
                                product=product, shop_name=shop_name,
                                defaults={'price': price, 'url': url_link, 'active': True}
                            )
                            count += 1
                        except: continue
                
                self.stdout.write(self.style.SUCCESS(f'   ✅ {shop_name}: {count} produktov.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Chyba XML {shop_name}: {e}"))


    def import_cj_products(self):
        cj_url = "https://ads.api.cj.com/query"
        headers = { "Authorization": f"Bearer {CJ_CONFIG['token']}", "Content-Type": "application/json" }
        
        for advertiser in CJ_CONFIG["advertisers"]:
            adv_name = advertiser["name"]
            adv_id = advertiser["id"]
            manual_cat_name = advertiser["manual_cat"]
            
            self.stdout.write(f"⏳ CJ: Pripájam sa na {adv_name}...")
            
            total_imported_adv = 0
            page = 1
            
            while total_imported_adv < LIMIT_PER_CJ_ADVERTISER:
                current_offset = (page - 1) * BATCH_SIZE_CJ
                
                query = """
                query products($partnerIds: [ID!], $companyId: ID!, $limit: Int, $offset: Int, $pid: ID!) {
                    products(partnerIds: $partnerIds, companyId: $companyId, limit: $limit, offset: $offset) {
                        resultList {
                            title
                            description
                            ... on Shopping {
                                price { amount currency }
                                gtin
                                productType
                                imageLink
                            }
                            linkCode(pid: $pid) { clickUrl }
                        }
                    }
                }
                """
                
                variables = {
                    "partnerIds": [adv_id],
                    "companyId": CJ_CONFIG['cid'],
                    "pid": CJ_CONFIG['pid'],
                    "limit": BATCH_SIZE_CJ,
                    "offset": current_offset
                }

                try:
                    response = requests.post(cj_url, json={'query': query, 'variables': variables}, headers=headers, timeout=30)
                    
                    if response.status_code != 200:
                        if response.status_code == 400: break
                        time.sleep(2)
                        continue

                    data = response.json()
                    products_list = data.get('data', {}).get('products', {}).get('resultList', [])
                    
                    if not products_list: break

                    count_in_batch = 0
                    
                    with transaction.atomic():
                        for item in products_list:
                            try:
                                name = item.get('title')
                                if not name: continue
                                
                                price_info = item.get('price')
                                if not price_info: continue
                                if price_info.get('currency') != 'EUR': continue
                                
                                price_val = Decimal(price_info.get('amount'))

                                raw_category_text = item.get('productType') or ""
                                ean = item.get('gtin') or ""
                                
                                # Dôležité: Do textu uložíme "Hračky" aj názov eshopu, aby Sorter vedel, čo to je!
                                # Ale fyzicky produkt skončí v NEZARADENÉ.
                                final_orig_text = f"{manual_cat_name} | {adv_name} | {raw_category_text}"

                                product, _ = Product.objects.update_or_create(
                                    name=name[:255],
                                    defaults={
                                        'slug': slugify(f"cj-{adv_name}-{name}"[:200]), 
                                        'description': item.get('description', '')[:5000],
                                        'price': price_val,
                                        'image_url': item.get('imageLink', ''),
                                        'category': self.fallback_cat,  # <--- VŠETKO SEM
                                        'is_oversized': False,
                                        'ean': ean[:13],
                                        'original_category_text': final_orig_text[:499]
                                    }
                                )
                                
                                Offer.objects.update_or_create(
                                    product=product,
                                    shop_name=adv_name,
                                    defaults={'price': price_val, 'url': item.get('linkCode', {}).get('clickUrl', ''), 'active': True}
                                )
                                count_in_batch += 1
                            except: continue

                    total_imported_adv += count_in_batch
                    self.stdout.write(f"   -> Dávka {page}: {count_in_batch} ks")
                    
                    page += 1
                    gc.collect()

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"   ❌ Chyba: {e}"))
                    break

            self.stdout.write(self.style.SUCCESS(f" ✅ {adv_name}: {total_imported_adv} ks."))