from django.core.management.base import BaseCommand
import requests
import json
from products.models import Product, Category, Offer
from django.utils.text import slugify
from decimal import Decimal
import uuid

class Command(BaseCommand):
    help = 'Import Allegro (CJ Network) - ROBUST DEBUG'

    def handle(self, *args, **kwargs):
        # ---------------------------------------------------------
        # 👇 1. NASTAVENIA KONKRÉTNEHO OBCHODU
        # ---------------------------------------------------------
        SHOP_NAME = "Allegro"
        
        # ⚠️ SEM VLOŽ ID PRE ALLEGRO (napr. 5326577 alebo iné z tvojho CJ)
        ADVERTISER_ID = "7167444" 
        
        # Predvolená kategória
        DEFAULT_CAT_NAME = "Rozličný tovar" 
        DEFAULT_CAT_SLUG = "rozlicny-tovar"

        # ---------------------------------------------------------
        # 👇 2. FIXNÉ ÚDAJE (Overené)
        # ---------------------------------------------------------
        CJ_COMPANY_ID = "7864372"       
        CJ_WEBSITE_ID = "101646612"     
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
                self.stdout.write(self.style.WARNING(f"⚠️ CJ nenašiel žiadne produkty pre ID {ADVERTISER_ID}. Skontroluj ID."))
                return

            self.stdout.write(f"📦 Našiel som {total_found} produktov. Spracovávam...")

            count = 0
            errors = 0
            default_cat, _ = Category.objects.get_or_create(slug=DEFAULT_CAT_SLUG, defaults={'name': DEFAULT_CAT_NAME})

            for item in products_data:
                try:
                    name = item.get('title')
                    # OCHRANA: Ak je popis None, dáme prázdny text
                    description = item.get('description') or ""
                    
                    price_info = item.get('price')
                    # OCHRANA: Ak chýba cena, dáme 0
                    price = Decimal(price_info.get('amount')) if price_info else Decimal('0.00')
                    
                    # OCHRANA: Ak chýba obrázok, dáme prázdny string
                    image_url = item.get('imageLink') or ""
                    
                    link_code = item.get('linkCode')
                    affiliate_url = link_code.get('clickUrl') if link_code else ""
                    
                    category_text = item.get('productType') or DEFAULT_CAT_NAME
                    ean = item.get('gtin') or ""

                    if not name or not affiliate_url:
                        continue

                    # Kategória
                    cat_clean = category_text
                    if '>' in category_text:
                        cat_clean = category_text.split('>')[-1].strip()
                        
                    category, _ = Category.objects.get_or_create(
                        slug=slugify(cat_clean)[:50],
                        defaults={'name': cat_clean, 'parent': default_cat}
                    )

                    # Produkt
                    product = None
                    if ean and len(ean) > 6:
                        product = Product.objects.filter(ean=ean).first()
                    if not product:
                        product = Product.objects.filter(name=name).first()

                    # Uloženie / Update
                    if product:
                        product.price = price
                        product.category = category
                        if image_url:
                            product.image_url = image_url
                        if not product.ean and ean: product.ean = ean
                        product.save()
                    else:
                        unique_slug = f"{slugify(name)[:40]}-{str(uuid.uuid4())[:4]}"
                        product = Product.objects.create(
                            name=name,
                            slug=unique_slug,
                            description=description,
                            price=price,
                            category=category,
                            image_url=image_url,
                            ean=ean[:13]
                        )

                    Offer.objects.update_or_create(
                        product=product,
                        shop_name=SHOP_NAME, 
                        defaults={'price': price, 'url': affiliate_url, 'active': True}
                    )

                    count += 1
                    if count % 200 == 0:
                        self.stdout.write(f"✅ {count}...")

                except Exception as e:
                    errors += 1
                    if errors <= 5:
                        self.stdout.write(self.style.WARNING(f"⚠️ Chyba pri '{name}': {e}"))

            self.stdout.write(self.style.SUCCESS(f"🎉 Hotovo! {SHOP_NAME}: {count} (Chyby: {errors})"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Kritická chyba: {e}"))