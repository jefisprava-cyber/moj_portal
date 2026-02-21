import time
import json
import requests
import os
from django.core.management.base import BaseCommand
from products.models import Product, Category
from django.db import transaction

# 👇 VLOŽ SEM SVOJ KĽÚČ OD OPENAI (začína sa na sk-...)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

class Command(BaseCommand):
    help = 'AI SORTER: Inteligentne roztriedi a uzamkne problematické produkty.'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS("🤖 Štartujem AI Kontrolóra..."))

        if OPENAI_API_KEY == "sk-tvoj-tajny-kluc-vloz-sem":
            self.stdout.write(self.style.ERROR("❌ CHYBA: Zabudol si vložiť OpenAI API kľúč do skriptu!"))
            return

        # 1. ZÍSKAME VŠETKY KATEGÓRIE (Pre kontext pre AI)
        self.stdout.write("📦 Sťahujem zoznam tvojich kategórií pre AI...")
        categories = Category.objects.filter(is_active=True).values('id', 'name')
        
        # Vytvoríme čistý textový zoznam: "ID: 55 - Smartfóny"
        cat_list_text = "\n".join([f"ID: {c['id']} - {c['name']}" for c in categories])

        # 2. NÁJDEME PROBLÉMOVÉ PRODUKTY
        # Hľadáme produkty, ktoré ešte NIE SÚ ZAMKNUTÉ a sú v kategórii s názvom "NEZARADENÉ"
        # (Tu si to môžeš neskôr zmeniť, ak budeš chcieť kontrolovať iné kategórie)
        suspect_products = Product.objects.filter(
            is_category_locked=False,
            category__name__icontains="nezaradené" 
        )[:50] # Zoberieme naraz max 50 produktov (aby sme nepreťažili API)

        total_suspects = suspect_products.count()
        if total_suspects == 0:
            self.stdout.write(self.style.SUCCESS("✅ Nenašiel som žiadne problémové produkty na kontrolu."))
            return

        self.stdout.write(f"🔍 Našiel som {total_suspects} produktov. Posielam do OpenAI...")

        # 3. PRÍPRAVA DÁT PRE AI
        products_data = []
        for p in suspect_products:
            products_data.append({
                "product_id": p.id,
                "name": p.name,
                "original_supplier_category": p.original_category_text or "Neznáma"
            })

        # 4. VOLÁME OPENAI API
        prompt = f"""
        Si expert na e-commerce a tvojou úlohou je zatriediť produkty do presných kategórií môjho e-shopu.
        
        Tu je zoznam mojich platných kategórií vo formáte (ID - Názov):
        {cat_list_text}
        
        Tu je pole produktov vo formáte JSON:
        {json.dumps(products_data, ensure_ascii=False)}
        
        Tvoja úloha:
        Pre každý produkt nájdi najvhodnejšiu kategóriu z môjho zoznamu.
        Vráť mi striktne iba JSON pole v takomto formáte a nič iné (žiadny sprievodný text):
        [
            {{"product_id": 123, "category_id": 45}},
            {{"product_id": 124, "category_id": 89}}
        ]
        """

        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "gpt-4o-mini", # Najlacnejší a veľmi rýchly model
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0 # Chceme presnosť, nie kreativitu
        }

        try:
            self.stdout.write("⏳ Čakám na odpoveď od AI...")
            response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
            response.raise_for_status()
            
            result = response.json()
            ai_text = result['choices'][0]['message']['content']
            
            # Očistenie odpovede, ak by AI náhodou pridala do odpovede formátovanie (napr. ```json)
            ai_text = ai_text.replace("```json", "").replace("```", "").strip()
            
            sorted_data = json.loads(ai_text)

            # 5. ULOŽENIE DO DATABÁZY
            self.stdout.write("💾 Ukladám zmeny do databázy a ZAMYKÁM produkty...")
            
            updated_count = 0
            with transaction.atomic():
                for item in sorted_data:
                    try:
                        product = Product.objects.get(id=item['product_id'])
                        product.category_id = item['category_id']
                        product.is_category_locked = True # 🔒 TU SA ZAMKNE!
                        product.save(update_fields=['category', 'is_category_locked'])
                        updated_count += 1
                        self.stdout.write(f"   -> {product.name} presunutý do kategórie ID {item['category_id']}")
                    except Exception as ex:
                        self.stdout.write(self.style.WARNING(f"⚠️ Nepodarilo sa uložiť produkt {item.get('product_id')}: {ex}"))

            self.stdout.write(self.style.SUCCESS(f"🎉 HOTOVO! Úspešne roztriedených a zamknutých {updated_count} produktov."))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Nastala chyba pri spojení s AI alebo pri spracovaní: {e}"))