from django.core.management.base import BaseCommand
from products.models import Category, Product, Offer, Bundle  # <--- TU BOL CHÝBAJÚCI BUNDLE
import random

class Command(BaseCommand):
    help = 'Naplní databázu testovacími dátami pre Konfigurátor'

    def handle(self, *args, **kwargs):
        self.stdout.write("🗑️ Mažem staré dáta...")
        # Najprv vymažeme závislosti (Offer, Bundle) a potom Produkty
        Offer.objects.all().delete()
        Bundle.objects.all().delete() # Vymažeme staré balíčky
        Product.objects.all().delete()
        Category.objects.all().delete()

        self.stdout.write("🌱 Vytváram Kategórie...")
        cat_elek = Category.objects.create(name="Elektronika", slug="elektronika")
        cat_dom = Category.objects.create(name="Domácnosť", slug="domacnost")
        cat_sport = Category.objects.create(name="Šport", slug="sport")

        # Zoznam produktov pre testovanie
        products_data = [
            # Elektronika - Apple
            ("iPhone 15", cat_elek, "Apple"),
            ("iPhone 14 Pro", cat_elek, "Apple"),
            ("MacBook Air", cat_elek, "Apple"),
            
            # Elektronika - Samsung
            ("Galaxy S24", cat_elek, "Samsung"),
            ("Galaxy Tab S9", cat_elek, "Samsung"),
            ("Galaxy Watch", cat_elek, "Samsung"),
            
            # Elektronika - Sony
            ("PlayStation 5", cat_elek, "Sony"),
            ("Slúchadlá WH-1000XM5", cat_elek, "Sony"),
            
            # Domácnosť - Bosch (Pre náš balíček!)
            ("Vstavaná rúra Series 6", cat_dom, "Bosch"),
            ("Indukčná doska", cat_dom, "Bosch"),
            ("Umývačka riadu Silence", cat_dom, "Bosch"),
            ("Chladnička NoFrost", cat_dom, "Bosch"),
            ("Mikrovlnná rúra", cat_dom, "Bosch"),
            
            # Iné
            ("Vysávač V15", cat_dom, "Dyson"),
        ]

        self.stdout.write("🏭 Vytváram Produkty a Ponuky...")
        
        created_products = []

        for name, cat, brand in products_data:
            # Vytvor produkt
            prod = Product.objects.create(
                name=name,
                category=cat,
                brand=brand,
                description=f"Špičkový produkt {name} od značky {brand}. Ideálny pre vašu domácnosť.",
                image_url="https://via.placeholder.com/300?text=" + name.replace(" ", "+") # Lepší placeholder
            )
            created_products.append(prod)

            # Vytvor 3 rôzne ceny pre každý produkt
            base_price = random.randint(300, 1200)
            
            Offer.objects.create(product=prod, shop_name="Alza.sk", price=base_price, url="http://alza.sk")
            Offer.objects.create(product=prod, shop_name="Datart.sk", price=base_price - random.randint(10, 50), url="http://datart.sk")
            Offer.objects.create(product=prod, shop_name="TPD.sk", price=base_price + random.randint(10, 50), url="http://tpd.sk")

        self.stdout.write(self.style.SUCCESS(f"✅ Produkty vytvorené."))

        # --- VYTVORENIE BALÍČKA (BUNDLE) ---
        self.stdout.write("🎁 Vytváram Balíčky (Bundles)...")
        
        # Nájdi produkty Bosch
        bosch_products = Product.objects.filter(brand="Bosch")
        
        if bosch_products.exists():
            bundle = Bundle.objects.create(
                name="Kompletná kuchyňa Bosch Series 6",
                slug="kuchyna-bosch", 
                description="Zostava spotrebičov pre modernú domácnosť. Nemecká kvalita a jednotný dizajn.",
                image_url="https://via.placeholder.com/400x300?text=Kuchyna+Bosch"
            )
            # Pridáme produkty do balíčka (max 5)
            bundle.products.set(bosch_products[:5])
            bundle.save()
            self.stdout.write(f"   -> Vytvorený balíček: {bundle.name}")
            
        # Nájdi produkty Apple (Druhý balíček pre test)
        apple_products = Product.objects.filter(brand="Apple")
        if apple_products.exists():
            bundle2 = Bundle.objects.create(
                name="Apple Ekosystém Štart",
                slug="apple-start",
                description="iPhone, MacBook a všetko čo potrebujete pre prácu aj zábavu.",
                image_url="https://via.placeholder.com/400x300?text=Apple+Set"
            )
            bundle2.products.set(apple_products[:3])
            bundle2.save()
            self.stdout.write(f"   -> Vytvorený balíček: {bundle2.name}")
        
        self.stdout.write(self.style.SUCCESS(f"✅ HOTOVO! Databáza je naplnená."))