import os
import json
import requests
from django.core.management.base import BaseCommand
from products.models import Product, Category
from django.db import transaction

# Bezpečne natiahne kľúč z prostredia Renderu
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

class Command(BaseCommand):
    help = 'AI SORTER 2.0: Inteligentne roztriedi odpad s nízkym skóre a vyhodí maďarčinu do koša.'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS("🤖 Štartujem AI Kontrolóra (Verzia 2.0)..."))

        if not OPENAI_API_KEY:
            self.stdout.write(self.style.ERROR("❌ CHYBA: API kľúč nenájdený v prostredí (OPENAI_API_KEY)."))
            return

        # 1. Nájdenie kategórie KÔŠ (Uisti sa, že si ju vytvoril na webe)
        trash_cat = Category.objects.filter(name__icontains="Kôš").first()
        if not trash_cat:
            self.stdout.write(self.style.ERROR("❌ CHYBA: Nenašiel som kategóriu, ktorá obsahuje slovo 'Kôš'. Vytvor ju v administrácii!"))
            return
        
        self.stdout.write(f"🗑️ Kôš na odpad nájdený: ID {trash_cat.id} - {trash_cat.name}")

        # 2. Získame platné kategórie (BEZ NEZARADENÝCH A BEZ KOŠA)
        self.stdout.write("📦 Sťahujem čistý zoznam kategórií pre AI (bez 'Nezaradených')...")
        categories = Category.objects.filter(is_active=True).exclude(name__icontains="nezaradené").exclude(id=trash_cat.id).values('id', 'name')
        
        cat_list_text = "\n".join([f"ID: {c['id']} - {c['name']}" for c in categories])

        # 3. Nájdenie podozrivých produktov (Tých, kde mal ENGINE menej ako 30% istotu a nie sú zamknuté)
        suspect_products = Product.objects.filter(
            is_category_locked=False,
            category_confidence__lt=30.0
        )[:50]

        total_suspects = len(suspect_products)
        if total_suspects == 0:
            self.stdout.write(self.style.SUCCESS("✅ E-shop je dokonale uprataný! Nenašiel som žiadne produkty s nízkym skóre."))
            return

        self.stdout.write(f"🔍 Našiel som {total_suspects} produktov s nízkym skóre. Posielam do OpenAI...")

        products_data = []
        for p in suspect_products:
            products_data.append({
                "product_id": p.id,
                "name": p.name,
                "original_supplier_category": p.original_category_text or "Neznáma"
            })

        # 4. EXTRÉMNE PRÍSNY PROMPT PRE AI
        prompt = f"""
        Si expert na e-commerce. Tvojou úlohou je zatriediť ťažké a problémové produkty do presných kategórií môjho e-shopu.
        
        Tu je zoznam mojich platných kategórií (ID - Názov):
        {cat_list_text}
        
        ŠPECIÁLNE PRAVIDLO:
        Ak je názov produktu v cudzom jazyku (maďarčina, chorvátčina, atď.), nedáva absolútne zmysel, alebo sa volá 'Produkt bez názvu' či iný odpad, priraď mu STRIKTNE ID {trash_cat.id} (Kôš). Do mojich normálnych kategórií priradzuj len jasné, slovenské/české a legitímne produkty.
        
        Tu sú produkty vo formáte JSON:
        {json.dumps(products_data, ensure_ascii=False)}
        
        Vráť mi striktne iba JSON pole v tomto formáte a nič iné (žiadny sprievodný text ani formátovanie):
        [
            {{"product_id": 123, "category_id": 45}}
        ]
        """

        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0
        }

        try:
            self.stdout.write("⏳ Čakám na odpoveď od AI...")
            response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
            response.raise_for_status()
            
            result = response.json()
            ai_text = result['choices'][0]['message']['content']
            
            # Očistenie od backtickov, keby si ich AI vymyslela
            ai_text = ai_text.replace("```json", "").replace("```", "").strip()
            
            sorted_data = json.loads(ai_text)

            self.stdout.write("💾 Ukladám zmeny do databázy a ZAMYKÁM produkty...")
            
            updated_count = 0
            with transaction.atomic():
                for item in sorted_data:
                    try:
                        product = Product.objects.get(id=item['product_id'])
                        product.category_id = item['category_id']
                        product.is_category_locked = True
                        product.category_confidence = 100.0 # Po AI sme si už istí na 100%
                        product.save(update_fields=['category', 'is_category_locked', 'category_confidence'])
                        
                        # Pekný výpis do terminálu
                        if item['category_id'] == trash_cat.id:
                            self.stdout.write(f"   -> 🗑️ (Kôš) {product.name}")
                        else:
                            self.stdout.write(f"   -> ✅ (Roztriedené) {product.name} -> ID {item['category_id']}")
                        
                        updated_count += 1
                    except Exception as ex:
                        self.stdout.write(self.style.WARNING(f"⚠️ Chyba ukladania pre ID {item.get('product_id')}: {ex}"))

            self.stdout.write(self.style.SUCCESS(f"🎉 HOTOVO! AI roztriedila a zamkla {updated_count} produktov."))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Nastala chyba pri spojení s AI: {e}"))