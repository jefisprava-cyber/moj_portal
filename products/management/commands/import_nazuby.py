from django.core.management.base import BaseCommand
import requests
import json
from products.models import Product, Category, Offer
from django.utils.text import slugify
from decimal import Decimal
import uuid

class Command(BaseCommand):
    help = 'Import Nazuby (CJ Network) - API GraphQL'

    def handle(self, *args, **kwargs):
        # ---------------------------------------------------------
        # 👇 1. NASTAVENIA KONKRÉTNEHO OBCHODU
        # ---------------------------------------------------------
        SHOP_NAME = "Nazuby"
        ADVERTISER_ID = "4322334"  # ✅ Tvoje ID pre Nazuby
        
        # Predvolená kategória
        DEFAULT_CAT_NAME = "Zdravie a krása" 
        DEFAULT_CAT_SLUG = "zdravie-a-krasa"

        # ---------------------------------------------------------
        # 👇 2. TVOJE FIXNÉ ÚDAJE (Overené a správne)
        # ---------------------------------------------------------
        CJ_COMPANY_ID = "7864372"       # ✅ Správne ID
        CJ_WEBSITE_ID = "101646612"     # ✅ Správne PID
        CJ_TOKEN = "O2uledg8fW-ArSOgXxt2jEBB0Q"
        
        LIMIT = 5000
        API_URL = "https://ads.api.cj.com/query"
        
        self.stdout.write(f"⏳ Pripájam sa na CJ API ({SHOP_NAME})...")

        # GraphQL Query
        query = """
        query products($partnerIds: [ID!], $companyId: ID!, $limit: Int, $pid: ID!) {
            products(partnerIds: $partnerIds, companyId: $companyId, limit: $limit) {
                totalCount
                resultList {
                    title
                    description
                    
                    ... on Shopping {
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
            # Volanie API
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

            if total_found == 0:
                self.stdout.write(self.style.WARNING(f"⚠️ CJ nenašiel žiadne produkty pre ID {ADVERTISER_ID}."))
                return

            self.stdout.write(f"📦 Našiel som {total_found} produktov. Sťahujem prvých {LIMIT}...")

            count = 0
            # Vytvorenie základnej kategórie
            default_cat, _ = Category.objects.get_or_create(slug=DEFAULT_CAT_SLUG, defaults={'name': DEFAULT_CAT_NAME})

            for item in products_data:
                try:
                    name = item.get('title')
                    description = item.get('description') or ""
                    
                    # Cena a Obrázok
                    price_info = item.get('price')
                    price = Decimal(price_info.get('amount')) if price_info else Decimal('0.00')
                    image_url = item.get('imageLink')
                    
                    # Link
                    link_code = item.get('linkCode')
                    affiliate_url = link_code.get('clickUrl') if link_code else ""
                    
                    # Kategória a EAN
                    category_text = item.get('productType') or DEFAULT_CAT_NAME
                    ean = item.get('gtin') or ""

                    # Validácia
                    if not name or not price or not affiliate_url:
                        continue

                    # Kategória (Ošetrenie "Home > Health > Dental")
                    if category_text:
                        cat_clean = category_text.split('>')[-1].strip()
                        category, created = Category.objects.get_or_create(
                            slug=slugify(cat_clean)[:50],
                            defaults={'name': cat_clean, 'parent': default_cat}
                        )
                    else:
                        category = default_cat

                    # Identifikácia produktu (EAN -> Názov)
                    product = None
                    if ean and len(ean) > 6:
                        product = Product.objects.filter(ean=ean).first()
                    
                    if not product:
                        product = Product.objects.filter(name=name).first()

                    # Uloženie / Update
                    if product:
                        product.price = price
                        product.category = category
                        if not product.ean and ean: product.ean = ean
                        product.save()
                    else:
                        base_slug = slugify(name)[:40]
                        unique_slug = f"{base_slug}-{str(uuid.uuid4())[:4]}"
                        
                        product = Product.objects.create(
                            name=name,
                            slug=unique_slug,
                            description=description,
                            price=price,
                            category=category,
                            image_url=image_url,
                            ean=ean[:13]
                        )

                    # Offer (Ponuka)
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
                    if count % 50 == 0:
                        self.stdout.write(f"✅ {count}...")

                except Exception as e:
                    pass

            self.stdout.write(self.style.SUCCESS(f"🎉 Hotovo! Importovaných {count} produktov z {SHOP_NAME}."))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Kritická chyba: {e}"))