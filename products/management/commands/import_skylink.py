from django.core.management.base import BaseCommand
from products.models import Product, Category
from django.conf import settings
from cjpy import CJ
from django.utils.text import slugify

class Command(BaseCommand):
    help = 'Import produktov z CJ Affiliate'

    # ==========================================
    # 👇👇👇 TU ZMEŇ ID INZERENTA 👇👇👇
    CJ_ADVERTISER_ID = "5395330" 
    # ==========================================

    def handle(self, *args, **kwargs):
        cj = CJ(settings.CJ_DEVELOPER_KEY)
        
        self.stdout.write(f"Pripájam sa k CJ pre inzerenta ID: {self.CJ_ADVERTISER_ID}...")

        products = cj.get_products(
            website_id=settings.CJ_WEBSITE_ID,
            advertiser_ids=[self.CJ_ADVERTISER_ID],
            records_per_page=100
        )

        if not products:
            self.stdout.write(self.style.ERROR('Žiadne produkty nenájdené alebo chyba API.'))
            return

        count = 0
        for item in products:
            try:
                name = item.get('title')
                price = item.get('price')
                description = item.get('description', '')
                url = item.get('linkCode', {}).get('clickUrl')
                image_url = item.get('imageUrl')
                category_path = item.get('productCategory', '')

                if not name or not price:
                    continue

                # Kategória
                if category_path:
                    cat_name = category_path.split('>')[-1].strip()
                    category, _ = Category.objects.get_or_create(name=cat_name)
                else:
                    category, _ = Category.objects.get_or_create(name="Nezaradené")

                Product.objects.update_or_create(
                    original_url=url,
                    defaults={
                        'name': name,
                        'slug': slugify(name)[:200] + "-" + str(count),
                        'description': description,
                        'price': price,
                        'image_url': image_url,
                        'category': category,
                        'is_active': True
                    }
                )
                count += 1
                if count % 50 == 0:
                    self.stdout.write(f"   Spracovaných {count} produktov...")

            except Exception as e:
                continue

        self.stdout.write(self.style.SUCCESS(f'🎉 Import hotový! Uložených {count} produktov.'))