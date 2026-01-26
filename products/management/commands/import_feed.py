from django.core.management.base import BaseCommand
from products.models import Product, Category, Offer
import random

class Command(BaseCommand):
    help = 'Naplní databázu novou štruktúrou (Kategórie -> Produkty -> Ponuky)'

    def handle(self, *args, **kwargs):
        # 1. Vyčistiť staré dáta
        self.stdout.write("🧹 Mazem staré dáta...")
        Offer.objects.all().delete()
        Product.objects.all().delete()
        Category.objects.all().delete()

        # 2. Vytvoriť kategórie
        self.stdout.write("📂 Vytváram kategórie...")
        cat_elek = Category.objects.create(name="Elektronika", slug="elektronika")
        cat_mobil = Category.objects.create(name="Mobily", slug="mobily", parent=cat_elek)
        cat_laptop = Category.objects.create(name="Notebooky", slug="notebooky", parent=cat_elek)
        
        # 3. Zoznam produktov (Karty)
        products_data = [
            ("iPhone 15 Pro", cat_mobil, "iphone"),
            ("Samsung Galaxy S24", cat_mobil, "samsung-galaxy"),
            ("MacBook Air M3", cat_laptop, "laptop"),
            ("Sony WH-1000XM5", cat_elek, "headphones"),
            ("Dyson V15 Detect", cat_elek, "vacuum-cleaner"),
            ("PlayStation 5 Slim", cat_elek, "playstation"),
            ("GoPro HERO12", cat_elek, "camera"),
            ("iPad Air 5", cat_elek, "tablet"),
        ]
        
        shops = ["Alza", "Nay", "iStyle", "Datart", "Brloh", "iStore"]
        
        self.stdout.write("📦 Vytváram produkty a ponuky...")
        
        for name, cat, img_key in products_data:
            # Vytvorenie Produktu
            p = Product.objects.create(
                name=name, 
                category=cat, 
                image_url=f"https://loremflickr.com/400/400/{img_key}?lock={random.randint(1,1000)}"
            )
            
            # Vytvorenie 2-5 ponúk pre každý produkt
            chosen_shops = random.sample(shops, random.randint(2, 5))
            base_price = random.randint(300, 1200)
            
            for shop in chosen_shops:
                # Jemná variácia ceny
                price_variation = base_price + random.randint(-50, 50)
                
                Offer.objects.create(
                    product=p,
                    shop_name=shop,
                    price=price_variation,
                    delivery_days=random.randint(1, 5),
                    url=f"https://google.com/search?q={name}+{shop}"
                )
        
        self.stdout.write(self.style.SUCCESS('✅ Hotovo! Databáza bola úspešne pregenerovaná.'))