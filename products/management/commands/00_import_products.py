import ssl
import urllib.request
import xml.etree.ElementTree as ET
import requests
import json
import time
import gc
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.utils.text import slugify
from products.models import Product, Category, Offer
from django.db import transaction

# ==========================================
# 🎯 ŠPECIALIZÁCIA (Zameranie e-shopu)
# ==========================================
TARGET_KEYWORDS = ["elektronika", "mobil", "smartfon", "televizor", "notebook", "pc", "sluchadla", "audio"]

# ==========================================
# 🎛️ HLAVNÉ VYPÍNAČE A LIMITY
# ==========================================
RUN_XML_IMPORT = True    
RUN_CJ_IMPORT = True     

# ⚠️ LIMITY
LIMIT_PER_CJ_ADVERTISER = 100000    
LIMIT_XML_PRODUCTS = 100000         
BATCH_SIZE_CJ = 500              

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

CJ_CONFIG = {
    "token": "O2uledg8fW-ArSOgXxt2jEBB0Q", 
    "cid": "7864372",    
    "pid": "101646612",  
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
    help = 'SMART SYNC PIPELINE: Inteligentná aktualizácia bez preťaženia'

    def handle(self, *args, **options):
        self.stdout.write("🚀 ŠTARTUJEM SMART SYNC IMPORT (Iba nové produkty a aktualizácia cien)...")
        if TARGET_KEYWORDS:
            self.stdout.write(self.style.WARNING(f"🎯 ZAPNUTÝ FILTER! Sťahujem len: {', '.join(TARGET_KEYWORDS)}"))
        
        self.fallback_cat, _ = Category.objects.get_or_create(
            name="NEZARADENÉ (IMPORT)", 
            defaults={'slug': 'nezaradene-import', 'is_active': False}
        )

        if RUN_XML_IMPORT:
            self.stdout.write("\n📡 --- FÁZA 1: XML FEEDY ---")
            for feed in XML_FEEDS:
                try:
                    self.import_xml_feed(feed["url"], feed["name"])
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"❌ Chyba {feed['name']}: {e}"))
                gc.collect() 
        
        if RUN_CJ_IMPORT:
            self.stdout.write("\n📡 --- FÁZA 2: CJ API ---")
            self.import_cj_products()
        
        self.stdout.write(self.style.SUCCESS("\n🎉 IMPORT DOKONČENÝ. Odovzdávam štafetu ENGINE SORTER-u..."))
        try:
            call_command('15_engine_sorter')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Chyba pri spúšťaní Engine Sortera: {e}"))

    def import_xml_feed(self, url, shop_name):
        self.stdout.write(f"⏳ XML: Sťahujem {shop_name}...")
        context = ssl._create_unverified_context()
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        
        try:
            with urllib.request.urlopen(req, context=context) as response:
                count_new = 0
                count_updated = 0
                
                for event, item in ET.iterparse(response, events=('end',)):
                    tag_name = item.tag.split('}')[-1].lower() 
                    
                    if tag_name in ['item', 'shopitem']:
                        if (count_new + count_updated) >= LIMIT_XML_PRODUCTS: 
                            break
                            
                        try:
                            def get_text(element, search_tags):
                                for child in element:
                                    if child.tag.split('}')[-1].lower() in search_tags:
                                        return child.text
                                return None

                            name = get_text(item, ['productname', 'title'])
                            xml_cat = get_text(item, ['categorytext', 'product_type']) or ""
                            
                            if not name:
                                item.clear()
                                continue

                            if TARGET_KEYWORDS:
                                check_text = (name + " " + xml_cat).lower()
                                if not any(kw in check_text for kw in TARGET_KEYWORDS):
                                    item.clear()
                                    continue
                                    
                            price_str = get_text(item, ['price_vat', 'price'])
                            if not price_str: 
                                item.clear()
                                continue
                                
                            price_str_clean = price_str.replace(',', '.').replace('EUR', '').replace('€', '').strip()
                            try: price = Decimal(price_str_clean)
                            except: 
                                item.clear()
                                continue

                            url_link = get_text(item, ['url', 'link']) or ""

                            with transaction.atomic():
                                product = Product.objects.filter(name=name[:255]).first()
                                if product:
                                    # SMART SYNC: Produkt existuje, updatujeme IBA cenu!
                                    if product.price != price:
                                        product.price = price
                                        product.save(update_fields=['price'])
                                    
                                    Offer.objects.update_or_create(
                                        product=product, shop_name=shop_name,
                                        defaults={'price': price, 'url': url_link, 'active': True}
                                    )
                                    count_updated += 1
                                else:
                                    # NOVÝ PRODUKT: Ukladáme kompletne všetko
                                    clean_cat = xml_cat.replace('|', '>').split('>')[-1].strip()
                                    ean = get_text(item, ['ean', 'gtin'])
                                    img_url = get_text(item, ['imgurl', 'image_link']) or ""
                                    desc = get_text(item, ['description']) or ""

                                    product = Product.objects.create(
                                        name=name[:255],
                                        slug=slugify(f"{shop_name}-{name}-{ean}"[:200]),
                                        description=desc[:5000],
                                        price=price,
                                        image_url=img_url,
                                        ean=ean[:13] if ean else None,
                                        category=self.fallback_cat,
                                        category_confidence=0.0,
                                        is_oversized=False,
                                        original_category_text=xml_cat[:499] if xml_cat else clean_cat[:499]
                                    )
                                    Offer.objects.update_or_create(
                                        product=product, shop_name=shop_name,
                                        defaults={'price': price, 'url': url_link, 'active': True}
                                    )
                                    count_new += 1
                                
                        except Exception: 
                            pass
                        
                        item.clear()
                
                self.stdout.write(self.style.SUCCESS(f'   ✅ {shop_name}: Nové: {count_new} | Aktualizované: {count_updated}'))
                
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
            
            total_new = 0
            total_updated = 0
            page = 1
            
            while (total_new + total_updated) < LIMIT_PER_CJ_ADVERTISER:
                current_offset = (page - 1) * BATCH_SIZE_CJ
                
                query = """
                query products($partnerIds: [ID!], $companyId: ID!, $limit: Int, $offset: Int, $pid: ID!, $keywords: [String!]) {
                    products(partnerIds: $partnerIds, companyId: $companyId, limit: $limit, offset: $offset, keywords: $keywords) {
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
                
                if TARGET_KEYWORDS:
                    variables["keywords"] = TARGET_KEYWORDS

                try:
                    response = requests.post(cj_url, json={'query': query, 'variables': variables}, headers=headers, timeout=30)
                    
                    if response.status_code != 200:
                        if response.status_code == 400: break
                        time.sleep(2)
                        continue

                    data = response.json()
                    products_list = data.get('data', {}).get('products', {}).get('resultList', [])
                    
                    if not products_list: break

                    batch_new = 0
                    batch_updated = 0
                    
                    with transaction.atomic():
                        for item in products_list:
                            try:
                                name = item.get('title')
                                if not name: continue
                                
                                price_info = item.get('price')
                                if not price_info: continue
                                if price_info.get('currency') != 'EUR': continue
                                
                                price_val = Decimal(price_info.get('amount'))

                                product = Product.objects.filter(name=name[:255]).first()
                                if product:
                                    # SMART SYNC: Updatujeme len cenu
                                    if product.price != price_val:
                                        product.price = price_val
                                        product.save(update_fields=['price'])
                                    
                                    Offer.objects.update_or_create(
                                        product=product, shop_name=adv_name,
                                        defaults={'price': price_val, 'url': item.get('linkCode', {}).get('clickUrl', ''), 'active': True}
                                    )
                                    batch_updated += 1
                                else:
                                    # NOVÝ PRODUKT
                                    raw_category_text = item.get('productType') or ""
                                    ean = item.get('gtin') or ""
                                    final_orig_text = f"{manual_cat_name} | {adv_name} | {raw_category_text}"

                                    product = Product.objects.create(
                                        name=name[:255],
                                        slug=slugify(f"cj-{adv_name}-{name}"[:200]),
                                        description=item.get('description', '')[:5000],
                                        price=price_val,
                                        image_url=item.get('imageLink', ''),
                                        category=self.fallback_cat,
                                        category_confidence=0.0,
                                        is_oversized=False,
                                        ean=ean[:13] if ean else None,
                                        original_category_text=final_orig_text[:499]
                                    )
                                    Offer.objects.update_or_create(
                                        product=product, shop_name=adv_name,
                                        defaults={'price': price_val, 'url': item.get('linkCode', {}).get('clickUrl', ''), 'active': True}
                                    )
                                    batch_new += 1
                            except: continue

                    total_new += batch_new
                    total_updated += batch_updated
                    self.stdout.write(f"   -> Dávka {page}: {batch_new} nových, {batch_updated} aktualizovaných")
                    
                    page += 1
                    gc.collect()

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"   ❌ Chyba: {e}"))
                    break

            self.stdout.write(self.style.SUCCESS(f" ✅ {adv_name}: {total_new} nových | {total_updated} aktualizovaných."))