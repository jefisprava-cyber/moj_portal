from django.core.management.base import BaseCommand
import requests
import json
from products.models import Product, Category, Offer
from django.utils.text import slugify
from decimal import Decimal
import uuid

class Command(BaseCommand):
    help = 'Import Allegro - SAFE MODE (Len sťahuje, netriedi)'

    def handle(self, *args, **kwargs):
        # --- NASTAVENIA ---
        SHOP_NAME = "Allegro"
        ADVERTISER_ID = "7167444" 
        CJ_COMPANY_ID = "7864372"       
        CJ_WEBSITE_ID = "101646612"     
        CJ_TOKEN = "O2uledg8fW-ArSOgXxt2jEBB0Q"
        LIMIT = 2000  # Môžeš zvýšiť ak chceš viac produktov
        API_URL = "https://ads.api.cj.com/query"
        
        self.stdout.write(f"⏳ Pripájam sa na CJ API ({SHOP_NAME})...")

        # 1. Získame záchrannú kategóriu
        safe_cat, _ = Category.objects.get_or_create(
            slug="nezaradene-temp", 
            defaults={'name': "NEZARADENÉ", 'is_active': False}
        )

        query = """
        query products($partnerIds: [ID!], $companyId: ID!, $limit: Int, $pid: ID!) {
            products(partnerIds: $partnerIds, companyId: $companyId, limit: $limit) {
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
            "limit": LIMIT
        }
        headers = { "Authorization": f"Bearer {CJ_TOKEN}", "Content-Type": "application/json" }

        try:
            response = requests.post(API_URL, json={'query': query, 'variables': variables}, headers=headers)
            data = response.json()
            products_data = data.get('data', {}).get('products', {}).get('resultList', [])
            
            if not products_data:
                self.stdout.write(self.style.WARNING("⚠️ Žiadne produkty."))
                return

            self.stdout.write(f"📦 Spracovávam {len(products_data)} produktov...")

            count = 0
            for item in products_data:
                try:
                    name = item.get('title')
                    if not name: continue

                    price_info = item.get('price')
                    price = Decimal(price_info.get('amount')) if price_info else Decimal('0.00')
                    image_url = item.get('imageLink') or ""
                    affiliate_url = item.get('linkCode', {}).get('clickUrl', "")
                    
                    # Uložíme pôvodný text kategórie (napr. "Heureka | Elektronika | Mobily")
                    raw_category_text = item.get('productType') or ""
                    ean = item.get('gtin') or ""

                    # Hľadáme existujúci produkt
                    product = None
                    if ean and len(ean) > 6:
                        product = Product.objects.filter(ean=ean).first()
                    if not product:
                        product = Product.objects.filter(name=name).first()

                    # Uloženie / Update
                    if product:
                        product.price = price
                        # Kategóriu nemeníme, ak už je zatriedený inam ako v Nezaradené
                        if product.category.slug == "nezaradene-temp":
                             product.category = safe_cat
                        
                        if image_url: product.image_url = image_url
                        product.original_category_text = raw_category_text # Aktualizujeme pomocný text
                        product.save()
                    else:
                        unique_slug = f"{slugify(name)[:40]}-{str(uuid.uuid4())[:4]}"
                        product = Product.objects.create(
                            name=name,
                            slug=unique_slug,
                            description=item.get('description') or "",
                            price=price,
                            category=safe_cat, # VŽDY do Nezaradené
                            image_url=image_url,
                            ean=ean[:13],
                            original_category_text=raw_category_text
                        )

                    Offer.objects.update_or_create(
                        product=product,
                        shop_name=SHOP_NAME, 
                        defaults={'price': price, 'url': affiliate_url, 'active': True}
                    )
                    count += 1
                except Exception: continue

            self.stdout.write(self.style.SUCCESS(f"🎉 Import hotový: {count} produktov."))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Chyba: {e}"))