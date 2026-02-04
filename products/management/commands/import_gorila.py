from django.core.management.base import BaseCommand
import requests
import json
from products.models import Product, Category, Offer
from django.utils.text import slugify
from decimal import Decimal
import uuid

class Command(BaseCommand):
    help = 'Import produktov z Gorila.sk (CJ Network) - FINAL FIX'

    def handle(self, *args, **kwargs):
        # --- FINÁLNE ÚDAJE ---
        CJ_COMPANY_ID = "7864372"
        CJ_WEBSITE_ID = "101646612"
        ADVERTISER_ID = "5284767"  # Gorila
        CJ_TOKEN = "O2uledg8fW-ArSOgXxt2jEBB0Q"
        
        SHOP_NAME = "Gorila.sk"
        LIMIT = 100

        API_URL = "https://ads.api.cj.com/query"
        
        self.stdout.write(f"⏳ Pripájam sa na CJ API (Gorila)...")

        # OPRAVA 1: $partnerIds musí byť [ID!], nie [String!]
        query = """
        query products($partnerIds: [ID!], $companyId: ID!, $limit: Int, $pid: ID!) {
            products(partnerIds: $partnerIds, companyId: $companyId, limit: $limit) {
                totalCount
                resultList {
                    title
                    description
                    
                    # OPRAVA 2: Všetky nákupné polia musia byť tu
                    ... on ShoppingProduct {
                        price {
                            amount
                            currency
                        }
                        gtin
                        productType
                        imageLink
                    }

                    linkCode(pid: $pid) {
                        clickUrl
                    }
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

        headers = {
            "Authorization": f"Bearer {CJ_TOKEN}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(API_URL, json={'query': query, 'variables': variables}, headers=headers)
            
            if response.status_code != 200:
                self.stdout.write(self.style.ERROR(f"❌ Chyba {response.status_code}"))
                self.stdout.write(self.style.WARNING(f"📩 {response.text}"))
                return

            data = response.json()
            
            if 'errors' in data:
                self.stdout.write(self.style.ERROR(f"❌ Chyba API: {json.dumps(data['errors'], indent=2)}"))
                return

            products_data = data.get('data', {}).get('products', {}).get('resultList', [])
            total_found = data.get('data', {}).get('products', {}).get('totalCount', 0)

            self.stdout.write(f"📦 Našiel som {total_found} produktov. Sťahujem prvých {LIMIT}...")

            count = 0
            default_cat, _ = Category.objects.get_or_create(slug='knihy-a-zabava', defaults={'name': 'Knihy a Zábava'})

            for item in products_data:
                try:
                    name = item.get('title')
                    description = item.get('description') or ""
                    
                    price_info = item.get('price')
                    price = Decimal(price_info.get('amount')) if price_info else Decimal('0.00')
                    image_url = item.get('imageLink')
                    
                    link_code = item.get('linkCode')
                    affiliate_url = link_code.get('clickUrl') if link_code else ""
                    
                    category_text = item.get('productType') or "Knihy"
                    ean = item.get('gtin') or ""

                    if not name or not price or not affiliate_url:
                        continue

                    category, created = Category.objects.get_or_create(
                        slug=slugify(category_text)[:50],
                        defaults={'name': category_text, 'parent': default_cat}
                    )

                    base_slug = slugify(name)[:40]
                    unique_slug = f"{base_slug}-{str(uuid.uuid4())[:4]}"

                    product, created = Product.objects.get_or_create(
                        name=name,
                        defaults={
                            'slug': unique_slug,
                            'description': description,
                            'price': price,
                            'category': category,
                            'image_url': image_url,
                            'ean': ean[:13]
                        }
                    )

                    Offer.objects.update_or_create(
                        product=product,
                        shop_name=SHOP_NAME, 
                        defaults={
                            'price': price,
                            'url': affiliate_url,
                            'active': True
                        }
                    )

                    count += 1
                    if count % 10 == 0:
                        self.stdout.write(f"✅ {count}. {name[:30]}...")

                except Exception as e:
                    pass

            self.stdout.write(self.style.SUCCESS(f"🎉 Hotovo! Importovaných {count} produktov z {SHOP_NAME}."))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Kritická chyba: {e}"))