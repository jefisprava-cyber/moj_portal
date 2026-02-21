import csv
import requests
import io
import time
import gc
import unicodedata
import re
from django.core.management.base import BaseCommand
from products.models import Product, Category
from django.utils.text import slugify
from django.core.paginator import Paginator

class Command(BaseCommand):
    help = 'ENTERPRISE ENGINE: Normalizácia textu + Scoring systém + Confidence Score'

    def normalize_text(self, text):
        """Kriticky dôležité: Odstráni diakritiku, dá malé písmená a vyčistí znaky."""
        if not text:
            return ""
        # 1. Malé písmená
        text = str(text).lower()
        # 2. Odstránenie diakritiky (mäkčene, dĺžne)
        text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('utf-8')
        # 3. Ponechá len písmená, čísla a medzery
        text = re.sub(r'[^a-z0-9\s]', ' ', text)
        # 4. Zmaže viacnásobné medzery
        return ' '.join(text.split())

    def handle(self, *args, **kwargs):
        SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSQyXzkFCoyV5w2J36oMvrba9EhjyzrmLyBBk9UkyFpHEVYWbaFMqewAU9N91hDvUR_f-0wDseQgbKD/pub?output=csv"
        BATCH_SIZE = 1000  

        start_time = time.time()
        self.stdout.write(self.style.SUCCESS("🚀 Štartujem ENTERPRISE CATEGORY MATCH ENGINE..."))
        
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

            # Normalizujeme všetky kľúčové slová z tabuľky!
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
        all_ids = Product.objects.filter(is_category_locked=False).values_list('id', flat=True).order_by('id')
        paginator = Paginator(all_ids, BATCH_SIZE)
        
        total_matched = 0

        for page_num in paginator.page_range:
            page_ids = paginator.page(page_num).object_list
            self.stdout.write(f"   🔄 Dávka {page_num}/{paginator.num_pages} ({len(page_ids)} produktov)...")

            products_batch = Product.objects.filter(id__in=page_ids).only('id', 'name', 'original_category_text', 'brand', 'category_id', 'category_confidence')
            updates = []

            for p in products_batch:
                # 1. Spojenie a normalizácia textu produktu
                raw_text = f"{p.name} {p.original_category_text or ''} {p.brand or ''}"
                product_text = self.normalize_text(raw_text)
                
                best_score = -9999
                best_cat_id = None

                # 2. Testovanie proti všetkým pravidlám
                for rule in processed_rules:
                    score = 0
                    
                    # A) OUT pravidlo: Ak obsahuje zakázané slovo, dostane -100 bodov a okamžite letí von
                    if any(bad in product_text for bad in rule['out'] if bad):
                        score -= 100
                        continue 

                    # B) MUST pravidlo: Musí mať aspoň jedno z týchto slov, inak padá
                    if rule['must']:
                        if not any(good in product_text for good in rule['must'] if good):
                            continue

                    # C) IN pravidlo: +10 bodov za každé nájdené slovo
                    matches = 0
                    for key in rule['in']:
                        if key and key in product_text:
                            matches += 1
                            score += 10
                            # Bonus za presný match značky
                            if p.brand and self.normalize_text(p.brand) == key:
                                score += 15

                    if matches > 0:
                        score += rule['priority'] # Prirátame prioritu ako bonus
                        
                        # Ak je toto skóre zatiaľ najlepšie, uložíme ho ako víťaza
                        if score > best_score:
                            best_score = score
                            best_cat_id = rule['id']

                # 3. Vyhodnotenie víťaza a Confidence Score
                if best_cat_id:
                    # Výpočet istoty (Confidence): Každý +10 bodový zásah je zhruba 25% istota
                    # Max istota je 100% (napr. 4 zhody)
                    confidence = min(max(best_score * 2.5, 10.0), 100.0)
                    
                    if p.category_id != best_cat_id or p.category_confidence != confidence:
                        p.category_id = best_cat_id
                        p.category_confidence = confidence
                        updates.append(p)
                else:
                    # Nenašlo sa nič, confidence je 0
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
        