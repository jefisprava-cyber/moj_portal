from django.core.management.base import BaseCommand
from products.models import Product, Category, Offer
from django.conf import settings
from django.utils.text import slugify
import requests
import uuid
from decimal import Decimal

class Command(BaseCommand):
    help = 'Import produktov z CJ Affiliate - KancelarskeStolicky'

    def handle(self, *args, **kwargs):
        # 1. NASTAVENIA
        CJ_ADVERTISER_ID = "5493235"  # Inzerent: KancelarskeStolicky
        
        # 👇👇👇 TU JE TVOJE CID (ACCOUNT ID) 👇👇👇
        CJ_COMPANY_ID = "7864372" 

        try:
            CJ_WEBSITE_ID = settings.CJ_WEBSITE_ID # 101646612
            CJ_TOKEN = settings.CJ_DEVELOPER_KEY
        except AttributeError:
            self.stdout.write(self.style.ERROR("❌ CHYBA: Chýbajú nastavenia v settings.py"))
            return

        self.stdout.write(f"⏳ Pripájam sa na CJ API (ShoppingProducts)...")

        # 2. QUERY
        query = """
        query {
            shoppingProducts(
                companyId: "%s", 
                partnerIds: ["%s"], 
                limit: 100
            ) {
                resultList {
                    title
                    description
                    price {
                        amount
                        currency
                    }
                    linkCode(pid: "%s") {
                        clickUrl
                    }
                    imageLink
                    productCategory
                }
            }
        }
        """ % (CJ_COMPANY_ID, CJ_ADVERTISER_ID, CJ_WEBSITE_ID)

        headers = {
            "Authorization": f"Bearer {CJ_TOKEN}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        # 3. ODOSLANIE
        try:
            response = requests.post("https://ads.api.cj.com/query", json={'query': query}, headers=headers)
            
            if response.status_code != 200:
                self.stdout.write(self.style.ERROR(f"❌ Chyba API ({response.status_code}): {response.text}"))
                return
            
            data = response.json()
            if 'errors' in data:
                self.stdout.write(self.style.ERROR(f"❌ API vrátilo chybu: {data['errors'][0]['message']}"))
                return

            products_list = data.get('data', {}).get('shoppingProducts', {}).get('resultList', [])

            if not products_list:
                self.stdout.write(self.style.WARNING("⚠️ Žiadne produkty sa nenašli."))
                return

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Chyba pripojenia: {e}"))
            return

        # 4. ULOŽENIE
        count = 0
        default_cat, _ = Category.objects.get_or_create(slug='kancelaria', defaults={'name': 'Kancelária'})

        self.stdout.write("🚀 Začínam ukladanie produktov...")

        for item in products_list:
            try:
                name = item.get('title')
                price_val = item.get('price', {}).get('amount')
                desc = item.get('description', '')
                url = item.get('linkCode', {}).get('clickUrl')
                img = item.get('imageLink')
                cat_raw = item.get('productCategory', '')

                if not name or not price_val: continue

                if cat_raw:
                    cat_name = cat_raw.split('>')[-1].strip()
                    category, _ = Category.objects.get_or_create(slug=slugify(cat_name)[:50], defaults={'name': cat_name, 'parent': default_cat})
                else:
                    category = default_cat

                unique_slug = f"{slugify(name)[:150]}-{str(uuid.uuid4())[:4]}"
                price = Decimal(str(price_val))

                product, created = Product.objects.update_or_create(
                    original_url=url,
                    defaults={
                        'name': name,
                        'slug': unique_slug if created else slugify(name)[:150] + "-" + str(count),
                        'description': desc,
                        'price': price,
                        'category': category,
                        'image_url': img,
                        'is_active': True
                    }
                )
                
                Offer.objects.update_or_create(
                    product=product,
                    shop_name="KancelarskeStolicky",
                    defaults={'price': price, 'url': url, 'active': True}
                )
                count += 1
            except Exception: continue

        self.stdout.write(self.style.SUCCESS(f"🎉 Hotovo! {count} produktov."))