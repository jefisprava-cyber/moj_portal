from django.core.management.base import BaseCommand
from products.models import Product, Offer, Category, Bundle, PriceHistory
from django.utils.text import slugify
import random
from datetime import timedelta, date
from django.db.models import Min

class Command(BaseCommand):
    help = 'Importuje testovacie dáta a generuje históriu cien'

    def handle(self, *args, **kwargs):
        self.stdout.write("🗑️  Mažem staré dáta...")
        # Zmažeme všetko, aby sme nemali duplicity
        PriceHistory.objects.all().delete()
        Offer.objects.all().delete()
        Product.objects.all().delete()
        Category.objects.all().delete()
        Bundle.objects.all().delete()

        self.stdout.write("📦 Vytváram kategórie...")
        cat_elektronika = Category.objects.create(name="Elektronika", slug="elektronika")
        cat_mobily = Category.objects.create(name="Smartfóny", slug="smartfony", parent=cat_elektronika)
        cat_notebooky = Category.objects.create(name="Notebooky", slug="notebooky", parent=cat_elektronika)
        
        cat_domacnost = Category.objects.create(name="Domácnosť", slug="domacnost")
        cat_kuchyna = Category.objects.create(name="Kuchyňa", slug="kuchyna", parent=cat_domacnost)
        cat_velke_spotrebice = Category.objects.create(name="Veľké spotrebiče", slug="velke-spotrebice", parent=cat_domacnost)

        self.stdout.write("📱 Vytváram produkty...")
        products_data = [
            {"name": "Apple iPhone 15 128GB", "cat": cat_mobily, "price_range": (800, 950), "img": "https://store.storeimages.cdn-apple.com/4982/as-images.apple.com/is/iphone-15-black-select-202309?wid=512&hei=512&fmt=jpeg&qlt=90&.v=1692944326506"},
            {"name": "Samsung Galaxy S24", "cat": cat_mobily, "price_range": (750, 900), "img": "https://images.samsung.com/is/image/samsung/p6pim/sk/sm-s921bzkdeue/gallery/sk-galaxy-s24-sm-s921-sm-s921bzkdeue-539303555?$650_519_PNG$"},
            {"name": "MacBook Air M2", "cat": cat_notebooky, "price_range": (1100, 1300), "img": "https://store.storeimages.cdn-apple.com/4982/as-images.apple.com/is/macbook-air-midnight-select-20220606?wid=539&hei=312&fmt=jpeg&qlt=90&.v=1653084303665"},
            {"name": "Lenovo Legion 5", "cat": cat_notebooky, "price_range": (900, 1100), "img": "https://p1-ofp.static.pub/medias/bWFzdGVyfHJvb3R8MjUzMzEwfGltYWdlL3BuZ3xoZGEvaDIwLzE0MTkwNDQ1NDY1NjMwLnBuZ3w3YmI2M2E4NDQ3YjQ2YjBkZDE2YzE4YzE2ZDhkOWI1YjM4OGQ5ZjI5YzY4N2Y4YjI5gyZjE1NzFiYmYwYjI/lenovo-laptop-legion-5-15-amd-subseries-hero.png"},
            {"name": "Bosch Varná doska", "cat": cat_kuchyna, "price_range": (250, 400), "img": "https://media3.bosch-home.com/Product_Shots/1200x675/MCSA02652636_PUE611BB1E_def.jpg"},
            {"name": "Samsung Chladnička", "cat": cat_velke_spotrebice, "price_range": (450, 600), "is_oversized": True, "img": "https://images.samsung.com/is/image/samsung/sk-rb30j3000sa-rb30j3000sa-ef-001-front-silver?$720_576_PNG$"},
            {"name": "LG Práčka 8kg", "cat": cat_velke_spotrebice, "price_range": (350, 500), "is_oversized": True, "img": "https://www.lg.com/sk/images/pracky/md07530635/gallery/medium01.jpg"},
            {"name": "Sada hrncov Tefal", "cat": cat_kuchyna, "price_range": (80, 150), "img": "https://www.tefal.sk/medias/?context=bWFzdGVyfHJvb3R8MjY2MDZ8aW1hZ2UvanBlZ3xoNGEvaDQ5LzE1OTY5NjQ4MjYzNzEwLmpwZ3w1YzYyYmQ4YjYyYjYyYjYyYjYyYjYyYjYyYjYyYjYyYjYyYjYyYjYyYjYyYjYyYjYy"}
        ]

        created_products = []
        shops = ["Alza.sk", "Datart.sk", "Mall.sk", "Nay.sk", "AndreaShop"]

        for data in products_data:
            p = Product.objects.create(
                name=data["name"],
                category=data["cat"],
                image_url=data.get("img"),
                description=f"Toto je skvelý produkt {data['name']} pre vašu potrebu.",
                is_oversized=data.get("is_oversized", False)
            )
            created_products.append(p)
            
            # Vytvorenie 3-5 ponúk pre každý produkt
            for _ in range(random.randint(3, 5)):
                price = round(random.uniform(*data["price_range"]), 2)
                shop = random.choice(shops)
                Offer.objects.create(
                    product=p,
                    shop_name=shop,
                    price=price,
                    url="https://example.com",
                    delivery_days=random.randint(1, 5)
                )

        self.stdout.write("🎁 Vytváram balíčky...")
        b1 = Bundle.objects.create(
            name="Študentský Starter Pack",
            slug="studentsky-pack",
            description="Všetko čo potrebuje študent na intrák.",
            image_url="https://images.unsplash.com/photo-1522202176988-66273c2fd55f?q=80&w=1000&auto=format&fit=crop"
        )
        b1.products.add(created_products[2], created_products[0]) # MacBook + iPhone

        b2 = Bundle.objects.create(
            name="Kompletná Kuchyňa",
            slug="kompletna-kuchyna",
            description="Zariaďte si kuchyňu naraz a ušetrite.",
            image_url="https://images.unsplash.com/photo-1556911220-e15b29be8c8f?q=80&w=1000&auto=format&fit=crop"
        )
        b2.products.add(created_products[4], created_products[5], created_products[7]) # Doska + Chladnička + Hrnce

        # --- NOVÉ: GENEROVANIE HISTÓRIE CIEN (Fiktívne dáta pre graf) ---
        self.stdout.write("📊 Generujem históriu cien (30 dní)...")
        
        today = date.today()
        
        for product in created_products:
            # Zistíme aktuálnu najnižšiu cenu
            current_min_price = product.offers.aggregate(Min('price'))['price__min']
            if not current_min_price: continue

            base_price = float(current_min_price)
            
            # Vygenerujeme ceny za posledných 30 dní
            for i in range(30, 0, -1):
                day = today - timedelta(days=i)
                
                # Simulácia: Cena trochu kolíše (+- 5%)
                fluctuation = random.uniform(-0.05, 0.05) 
                hist_price = base_price * (1 + fluctuation)
                
                # Občas urobíme "akciu" (výrazný pokles pred 10 dňami)
                if i == 10: 
                    hist_price = base_price * 1.2 # Pred 10 dňami bolo drahšie

                PriceHistory.objects.create(
                    product=product,
                    price=round(hist_price, 2),
                    date=day
                )
            
            # Pridáme dnešnú cenu
            PriceHistory.objects.create(product=product, price=base_price, date=today)

        self.stdout.write(self.style.SUCCESS("🚀 Hotovo! Databáza je naplnená aj s grafmi."))