import os
import django
from django.db import connection

# Nastavenie Django prostredia
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings') # Uisti sa, že 'core' je názov tvojej zložky so settings.py
django.setup()

from products.models import Review, Product, Offer

def run_fix():
    print("🚑 SPÚŠŤAM OPRAVU DATABÁZY...")
    
    with connection.schema_editor() as schema_editor:
        # 1. Vytvorenie tabuľky Review
        try:
            print("⏳ Pokus o vytvorenie tabuľky Review...")
            schema_editor.create_model(Review)
            print("✅ Tabuľka REVIEW vytvorená úspešne!")
        except Exception as e:
            print(f"⚠️ Tabuľka Review už asi existuje alebo iná chyba: {e}")

        # 2. Pridanie stĺpca is_sponsored
        try:
            print("⏳ Pokus o pridanie stĺpca is_sponsored...")
            field = Offer._meta.get_field('is_sponsored')
            schema_editor.add_field(Offer, field)
            print("✅ Stĺpec IS_SPONSORED pridaný!")
        except Exception as e:
            print(f"ℹ️ Stĺpec is_sponsored už existuje (to je OK).")

        # 3. Pridanie stĺpca average_rating
        try:
            print("⏳ Pokus o pridanie stĺpca average_rating...")
            field = Product._meta.get_field('average_rating')
            schema_editor.add_field(Product, field)
            print("✅ Stĺpec AVERAGE_RATING pridaný!")
        except Exception as e:
            print(f"ℹ️ Stĺpec average_rating už existuje (to je OK).")
            
        # 4. Pridanie stĺpca review_count
        try:
            print("⏳ Pokus o pridanie stĺpca review_count...")
            field = Product._meta.get_field('review_count')
            schema_editor.add_field(Product, field)
            print("✅ Stĺpec REVIEW_COUNT pridaný!")
        except Exception as e:
            print(f"ℹ️ Stĺpec review_count už existuje (to je OK).")

    print("🏁 OPRAVA DOKONČENÁ. Server by mal teraz nabehnúť.")

if __name__ == "__main__":
    run_fix()