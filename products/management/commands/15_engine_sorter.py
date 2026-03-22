import csv
import requests
import io
import time
import gc
import unicodedata
import re
from django.core.management.base import BaseCommand
from django.core.management import call_command
from products.models import Product, Category
from django.utils.text import slugify
from django.core.paginator import Paginator

class Command(BaseCommand):
    help = 'ENTERPRISE ENGINE: Full Scan (Oprava kategórií) + Presné celé slová + HEUREKA LOGIKA'

    def normalize_text(self, text):
        if not text:
            return ""
        text = str(text).lower()
        text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('utf-8')
        text = re.sub(r'[^a-z0-9\s]', ' ', text)
        return ' '.join(text.split())

    def handle(self, *args, **kwargs):
        SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSQyXzkFCoyV5w2J36oMvrba9EhjyzrmLyBBk9UkyFpHEVYWbaFMqewAU9N91hDvUR_f-0wDseQgbKD/pub?output=csv"
        BATCH_SIZE = 1000  

        start_time = time.time()
        self.stdout.write(self.style.SUCCESS("🚀 Štartujem ENTERPRISE CATEGORY MAPPER (Full Scan & Celé slová)..."))
        
        # --- ZISŤUJEME, ČI MÁME VÔBEC ČO ROBIŤ ---
        # 👇 ZAKOMENTOVANÝ SMART SYNC - Zapni, keď bude všetko upratané (odkomentuj tieto 4 riadky)
        # fallback_cat = Category.objects.filter(name='NEZARADENÉ (IMPORT)').first()
        # if fallback_cat:
        #     all_ids = list(Product.objects.filter(category=fallback_cat).values_list('id', flat=True).order_by('id'))
        # else:
        #     all_ids = []
            
        # 👇 ZAPNUTÝ FULL SCAN: Zoberie VŠETKY odomknuté produkty, aby opravil zlé zaradenia
        all_ids = list(Product.objects.filter(is_category_locked=False).values_list('id', flat=True).order_by('id'))
            
        if not all_ids:
            self.stdout.write(self.style.SUCCESS("✅ Žiadne produkty na roztriedenie. Sorter nemá čo robiť."))
            self.stdout.write(self.style.SUCCESS("\n🔍 ODOVZDÁVAM ŠTAFETU: Štartujem aktualizáciu vyhľadávania (16_update_search)..."))
            try:
                call_command('16_update_search')
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Chyba pri spúšťaní Update Search: {e}"))
            return
            
        self.stdout.write(f"🔎 Našiel som {len(all_ids)} produktov na roztriedenie/opravu...")

        # --- STIAHNUTIE PRAVIDIEL ---
        try:
            response = requests.get(SHEET_URL)
            response.raise_for_status()
            rules_data = list(csv.DictReader(io.StringIO(response.content.decode('utf-8'))))
            self.stdout.write(f"✅ Načítaných {len(rules_data)} pravidiel z Google Sheetu.")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Chyba siete: {e}"))
            return

        # --- BUDOVANIE STROMU A NORMALIZÁCIA PRAVIDIEL ---
        cat_cache = {}
        for c in Category.objects.all():
            cat_cache[(c.name, c.parent_id)] = c

        processed_rules = []
        levels = ['L1', 'L2', 'L3', 'L4', 'L5']

        for row_idx, row in enumerate(rules_data):
            parent_obj = None
            for level in levels:
                cat_name = row.get(level, '').strip()
                if not cat_name: continue

                cache_key = (cat_name, parent_obj.id if parent_obj else None)

                if cache_key in cat_cache:
                    parent_obj = cat_cache[cache_key]
                else:
                    new_slug = slugify(cat_name)[:200]
                    if Category.objects.filter(slug=new_slug).exists():
                         new_slug = f"{new_slug}-{row_idx}"

                    cat, _ = Category.objects.get_or_create(
                        name=cat_name, parent=parent_obj,
                        defaults={'slug': new_slug, 'is_active': True}
                    )
                    cat_cache[cache_key] = cat
                    parent_obj = cat
                    
            target_cat = parent_obj
            if not target_cat: continue

            in_raw = row.get('IN') or row.get('IN (Kľúčové slovo)') or ""
            out_raw = row.get('OUT') or ""
            must_raw = row.get('MUST') or ""
            
            try: priority = int(row.get('PRIORITY') or "0")
            except: priority = 0

            in_words = [self.normalize_text(w) for w in in_raw.split(',') if w.strip()]
            out_words = [self.normalize_text(w) for w in out_raw.split(',') if w.strip()]
            must_words = [self.normalize_text(w) for w in must_raw.split(',') if w.strip()]

            if in_words:
                processed_rules.append({
                    'id': target_cat.id,
                    'in': in_words,
                    'out': out_words,
                    'must': must_words,
                    'priority': priority
                })

        self.stdout.write("⚙️ Pravidlá znormalizované. Idem skórovať produkty...")

        # --- SCORING ALGORITMUS (BODOVANIE) ---
        paginator = Paginator(all_ids, BATCH_SIZE)
        total_matched = 0

        for page_num in paginator.page_range:
            page_ids = paginator.page(page_num).object_list
            self.stdout.write(f"   🔄 Dávka {page_num}/{paginator.num_pages} ({len(page_ids)} produktov)...")

            products_batch = Product.objects.filter(id__in=page_ids).only('id', 'name', 'original_category_text', 'brand', 'category_id', 'category_confidence')
            updates = []

            for p in products_batch:
                # 👇 KĽÚČOVÁ ZMENA 1: HEUREKA MAPOVAČ! 
                # Úplne sme vyhodili p.name a p.brand. Kontroluje sa IBA dodávateľská kategória.
                raw_text = p.original_category_text or ""
                product_text = self.normalize_text(raw_text)
                
                # 👇 Obalíme text medzerami na hľadanie celých slov!
                padded_text = f" {product_text} "
                
                best_score = -9999
                best_cat_id = None

                for rule in processed_rules:
                    score = 0
                    
                    # Hľadáme presné slová obalené medzerami
                    if any(f" {bad} " in padded_text for bad in rule['out'] if bad):
                        score -= 100
                        continue 

                    if rule['must']:
                        if not any(f" {good} " in padded_text for good in rule['must'] if good):
                            continue

                    matches = 0
                    for key in rule['in']:
                        if key and f" {key} " in padded_text:
                            matches += 1
                            score += 10

                    if matches > 0:
                        score += rule['priority'] 
                        
                        if score > best_score:
                            best_score = score
                            best_cat_id = rule['id']

                if best_cat_id:
                    confidence = min(max(best_score * 2.5, 10.0), 100.0)
                    
                    if p.category_id != best_cat_id or p.category_confidence != confidence:
                        p.category_id = best_cat_id
                        p.category_confidence = confidence
                        updates.append(p)
                else:
                    if p.category_confidence != 0.0:
                        p.category_confidence = 0.0
                        updates.append(p)

            if updates:
                Product.objects.bulk_update(updates, ['category', 'category_confidence'])
                total_matched += len(updates)
            
            del products_batch
            del updates
            gc.collect()

        self.stdout.write(self.style.SUCCESS(f"🎉 HOTOVO! Prekategorizovaných a obodovaných {total_matched} produktov."))
        self.stdout.write(f"🏁 Celkový čas: {time.time() - start_time:.2f} s")
        
        # 👇 TESTOVACÍ REŽIM: AI Sorter je odpojený
        self.stdout.write(self.style.SUCCESS("\n🛑 TESTOVACÍ REŽIM: AI Sorter (13) sa nespustí automaticky."))
        self.stdout.write(self.style.WARNING("👉 Teraz si môžeš v administrácii skontrolovať kategóriu 'NEZARADENÉ (IMPORT)'."))
        self.stdout.write(self.style.WARNING("👉 Keď budeš pripravený dotriediť zvyšok, spusti: python manage.py 13_ai_sorter"))
        
        # Ale vyhľadávač (16) spustíme, aby upratané produkty už boli na webe funkčné
        self.stdout.write(self.style.SUCCESS("\n🔍 ODOVZDÁVAM ŠTAFETU: Štartujem aktualizáciu vyhľadávania (16_update_search)..."))
        try:
            call_command('16_update_search')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Chyba pri spúšťaní Update Search: {e}"))