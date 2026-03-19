import csv
import requests
import time
from decimal import Decimal
from django.core.management.base import BaseCommand
from products.models import Product, Offer, Category
from django.utils.text import slugify
from django.db import transaction

class Command(BaseCommand):
    help = 'ULTIMÁTNY EXPORT: Sťahuje milióny CJ produktov cez CSV'

    def handle(self, *args, **options):
        # TENTO ODKAZ ZÍSKAŠ V CJ AFFILIATE SYSTÉME (Products -> Export)
        CSV_URL = "https://datatransfer.cj.com/example-export.csv" 
        
        self.stdout.write("🚀 ŠTARTUJEM CSV MASS IMPORT Z CJ AFFILIATE...")
        start_time = time.time()
        
        fallback_cat, _ = Category.objects.get_or_create(
            name="NEZARADENÉ (IMPORT)", 
            defaults={'slug': 'nezaradene-temp', 'is_active': False}
        )

        try:
            # Používame stream=True, aby sme miliónový súbor nestiahli celý do RAM!
            self.stdout.write("📥 Pripájam sa na CSV stream...")
            with requests.get(CSV_URL, stream=True) as r:
                r.raise_for_status()
                
                # Dekódujeme po riadkoch
                lines = (line.decode('utf-8') for line in r.iter_lines())
                reader = csv.DictReader(lines)
                
                count_new = 0
                count_updated = 0
                
                # Čítame riadok po riadku
                with transaction.atomic():
                    for row in reader:
                        # Stĺpce závisia od toho, ako si ich naklikáš v CJ exporte
                        name = row.get('Product Name')
                        price_str = row.get('Price')
                        url_link = row.get('Buy URL')
                        img_url = row.get('Image URL', '')
                        desc = row.get('Description', '')
                        ean = row.get('UPC', '')
                        shop_name = row.get('Program Name', 'Neznámy E-shop')
                        orig_cat = row.get('Category', '')
                        
                        if not name or not price_str:
                            continue
                            
                        try:
                            price = Decimal(price_str.replace(',', '.').strip())
                        except:
                            continue

                        product = Product.objects.filter(name=name[:255]).first()
                        
                        if product:
                            # SMART SYNC: Ak existuje, len updatneme cenu
                            if product.price != price:
                                product.price = price
                                product.save(update_fields=['price'])
                            
                            Offer.objects.update_or_create(
                                product=product, shop_name=shop_name,
                                defaults={'price': price, 'url': url_link, 'active': True}
                            )
                            count_updated += 1
                        else:
                            # NOVÝ PRODUKT
                            product = Product.objects.create(
                                name=name[:255],
                                slug=slugify(f"cjcsv-{shop_name}-{name}"[:200]),
                                description=desc[:5000],
                                price=price,
                                image_url=img_url,
                                ean=ean[:13] if ean else None,
                                category=fallback_cat,
                                category_confidence=0.0,
                                original_category_text=f"{shop_name} | {orig_cat}"[:499]
                            )
                            Offer.objects.update_or_create(
                                product=product, shop_name=shop_name,
                                defaults={'price': price, 'url': url_link, 'active': True}
                            )
                            count_new += 1
                            
                        # Každých 10 000 produktov vypíšeme stav
                        total = count_new + count_updated
                        if total % 10000 == 0:
                            self.stdout.write(f"   🔄 Spracovaných {total} produktov...")

            self.stdout.write(self.style.SUCCESS(f"🎉 HOTOVO! Nové: {count_new} | Aktualizované: {count_updated}"))
            self.stdout.write(f"🏁 Celkový čas: {time.time() - start_time:.2f} s")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Chyba sťahovania CSV: {e}"))