from django.core.management.base import BaseCommand
import requests
import json
from products.models import Product, Category, Offer
from django.utils.text import slugify
from decimal import Decimal
import uuid
import time
import gc

class Command(BaseCommand):
    help = 'Import Allegro - AUTOMAT (Sťahuje po 500 ks cez OFFSET)'

    def handle(self, *args, **kwargs):
        # --- NASTAVENIA ---
        SHOP_NAME = "Allegro"
        ADVERTISER_ID = "7167444" 
        CJ_COMPANY_ID = "7864372"       
        CJ_WEBSITE_ID = "101646612"     
        CJ_TOKEN = "O2uledg8fW-ArSOgXxt2jEBB0Q"
        
        BATCH_SIZE = 500       # Dávka
        MAX_TOTAL = 100000     # Cieľ
        API_URL = "https://ads.api.cj.com/query"
        
        self.stdout.write(f"🚀 Štartujem AUTOMATICKÝ IMPORT z {SHOP_NAME}...")
        self.stdout.write(f"   Cieľ: {MAX_TOTAL} produktov (v dávkach po {BATCH_SIZE})")

        # 1. Získame záchrannú kategóriu
        safe_cat, _ = Category.objects.get_or_create(
            slug="nezaradene-temp", 
            defaults={'name': "NEZARADENÉ", 'is_active': False}
        )

        # 2. Slučka
        total_saved = 0
        page = 1
        
        while total_saved < MAX_TOTAL:
            # Vypočítame OFFSET (koľko produktov preskočiť)
            current_offset = (page - 1) * BATCH_SIZE
            
            self.stdout.write(f"\n🔄 Sťahujem DÁVKU {page} (Offset: {current_offset})...")

            # 👇👇👇 ZMENA: Používame 'offset' namiesto 'page' 👇👇👇
            query = """
            query products($partnerIds: [ID!], $companyId: ID!, $limit: Int, $offset: Int, $pid: ID!) {
                products(partnerIds: $partnerIds, companyId: $companyId, limit: $limit, offset: $offset) {
                    totalCount
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
                "partnerIds": [ADVERTISER_ID],
                "companyId": CJ_COMPANY_ID,
                "pid": CJ_WEBSITE_ID,
                "limit": BATCH_SIZE,
                "offset": current_offset  # TOTO JE TÁ OPRAVA
            }
            headers = { "Authorization": f"Bearer {CJ_TOKEN}", "Content-Type": "application/json" }

            try:
                response = requests.post(API_URL, json={'query': query, 'variables': variables}, headers=headers)
                
                if response.status_code != 200:
                    self.stdout.write(self.style.ERROR(f"❌ Chyba API: {response.status_code}"))
                    self.stdout.write(f"   Detail: {response.text[:200]}") # Vypíše detail chyby
                    time.sleep(5)
                    # Ak je chyba 400 trvalá, breakneme, ale skúsime pokračovať
                    if response.status_code == 400:
                        break
                    continue

                data = response.json()
                products_data = data.get('data', {}).get('products', {}).get('resultList', [])
                
                if not products_data:
                    self.stdout.write(self.style.SUCCESS("🏁 Koniec zoznamu (API už neposlalo žiadne dáta)."))
                    break

                # Spracovanie
                count_in_batch = 0
                for item in products_data:
                    try:
                        name = item.get('title')
                        if not name: continue

                        price_info = item.get('price')
                        price = Decimal(price_info.get('amount')) if price_info else Decimal('0.00')
                        image_url = item.get('imageLink') or ""
                        affiliate_url = item.get('linkCode', {}).get('clickUrl', "")
                        raw_category_text = item.get('productType') or ""
                        ean = item.get('gtin') or ""

                        product = None
                        if ean and len(ean) > 6:
                            product = Product.objects.filter(ean=ean).first()
                        if not product:
                            product = Product.objects.filter(name=name).first()

                        if product:
                            product.price = price
                            if product.category.slug == "nezaradene-temp":
                                 product.category = safe_cat
                            if image_url: product.image_url = image_url
                            product.original_category_text = raw_category_text
                            product.save()
                        else:
                            unique_slug = f"{slugify(name)[:40]}-{str(uuid.uuid4())[:4]}"
                            product = Product.objects.create(
                                name=name,
                                slug=unique_slug,
                                description=item.get('description') or "",
                                price=price,
                                category=safe_cat,
                                image_url=image_url,
                                ean=ean[:13],
                                original_category_text=raw_category_text
                            )

                        Offer.objects.update_or_create(
                            product=product,
                            shop_name=SHOP_NAME, 
                            defaults={'price': price, 'url': affiliate_url, 'active': True}
                        )
                        count_in_batch += 1
                    except Exception: continue

                total_saved += count_in_batch
                self.stdout.write(f"   ✅ Uložených v dávke: {count_in_batch} (Celkovo: {total_saved})")
                
                page += 1
                del products_data
                del response
                gc.collect() 
                time.sleep(1)

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Kritická chyba v slučke: {e}"))
                break

        self.stdout.write(self.style.SUCCESS(f"🎉 KOMPLETNÝ IMPORT HOTOVÝ. Spolu spracovaných {total_saved} produktov."))