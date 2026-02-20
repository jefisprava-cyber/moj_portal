import csv
import requests
import io
import time
import gc
from django.core.management.base import BaseCommand
from products.models import Product, Category
from django.utils.text import slugify
from django.core.paginator import Paginator

class Command(BaseCommand):
    help = 'CHAIN SORTER 7.0: Priority + Multi-MUST + Memory Safe'

    def handle(self, *args, **kwargs):
        # ------------------------------------------------------------------
        # 👇 URL TVOJEJ TABUĽKY (Musí byť publikovaná ako CSV)
        # ------------------------------------------------------------------
        SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSQyXzkFCoyV5w2J36oMvrba9EhjyzrmLyBBk9UkyFpHEVYWbaFMqewAU9N91hDvUR_f-0wDseQgbKD/pub?output=csv"
        
        BATCH_SIZE = 1000  # Spracujeme 1000 produktov naraz (šetrí RAM)

        start_time = time.time()
        self.stdout.write("📊 Sťahujem dáta z Google Sheets (CSV)...")
        
        try:
            response = requests.get(SHEET_URL)
            response.raise_for_status()
            csv_content = response.content.decode('utf-8')
            # Načítame CSV do zoznamu slovníkov
            rules_data = list(csv.DictReader(io.StringIO(csv_content)))
            self.stdout.write(f"✅ Načítaných {len(rules_data)} riadkov pravidiel.")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Chyba siete: {e}"))
            return

        # ==================================================================
        # FÁZA 1: STROM KATEGÓRIÍ A PRÍPRAVA PRAVIDIEL
        # ==================================================================
        self.stdout.write("🌳 FÁZA 1: Budujem strom a analyzujem pravidlá...")
        
        cat_cache = {} # Cache pre kategórie: (slug, parent_id) -> id
        # Pred-načítame existujúce kategórie do cache
        for c in Category.objects.all():
            cat_cache[(c.name, c.parent_id)] = c

        levels = ['L1', 'L2', 'L3', 'L4', 'L5']
        processed_rules = []

        for row_idx, row in enumerate(rules_data):
            parent_obj = None
            
            # --- 1. Budovanie stromu ---
            for level in levels:
                cat_name = row.get(level, '').strip()
                if not cat_name: continue

                parent_id = parent_obj.id if parent_obj else None
                cache_key = (cat_name, parent_id)

                if cache_key in cat_cache:
                    parent_obj = cat_cache[cache_key]
                else:
                    # Vytvorenie novej kategórie
                    if parent_obj:
                        new_slug = f"{parent_obj.slug}-{slugify(cat_name)}"[:200]
                    else:
                        new_slug = slugify(cat_name)[:200]
                    
                    # Unikátnosť slugu
                    if Category.objects.filter(slug=new_slug).exists():
                         new_slug = f"{new_slug}-{row_idx}"

                    cat, _ = Category.objects.get_or_create(
                        name=cat_name,
                        parent=parent_obj,
                        defaults={'slug': new_slug, 'is_active': True}
                    )
                    cat_cache[cache_key] = cat
                    parent_obj = cat

            target_cat = parent_obj
            if not target_cat: continue

            # --- 2. Parsovanie pravidiel (PRIORITY, MUST, IN, OUT) ---
            # Získame dáta zo stĺpcov
            in_raw = row.get('IN') or row.get('IN (Kľúčové slovo)') or ""
            out_raw = row.get('OUT') or ""
            must_raw = row.get('MUST') or ""
            priority_raw = row.get('PRIORITY') or "0"

            # Konverzia na zoznamy (split podľa čiarky)
            in_words = [w.strip().lower() for w in in_raw.split(',') if w.strip()]
            out_words = [w.strip().lower() for w in out_raw.split(',') if w.strip()]
            
            # TU JE TÁ MAGIA PRE SYNONYMÁ V MUST:
            must_words = [w.strip().lower() for w in must_raw.split(',') if w.strip()]
            
            try:
                priority = int(priority_raw)
            except:
                priority = 0

            # Pravidlo uložíme len ak má nejaké IN slová
            if in_words:
                processed_rules.append({
                    'id': target_cat.id,
                    'in': in_words,
                    'out': out_words,
                    'must': must_words,
                    'priority': priority
                })

        self.stdout.write(self.style.SUCCESS(f"✅ Strom hotový. Pripravených {len(processed_rules)} pravidiel."))

        # ==================================================================
        # FÁZA 2: TRIEDENIE PRODUKTOV (MEMORY SAFE)
        # ==================================================================
        self.stdout.write("🧠 FÁZA 2: Triedim produkty (Bezpečný režim)...")

        # Získame len IDčka (to nezaberie pamäť)
        # 👇 UPRAVENÉ: Ignorujeme produkty, ktoré majú is_category_locked=True od AI
        all_ids = Product.objects.filter(is_category_locked=False).values_list('id', flat=True).order_by('id')
        paginator = Paginator(all_ids, BATCH_SIZE)
        
        total_matched = 0

        for page_num in paginator.page_range:
            page_ids = paginator.page(page_num).object_list
            self.stdout.write(f"   🔄 Dávka {page_num}/{paginator.num_pages} ({len(page_ids)} ks)...")

            # Načítame objekty len pre túto dávku
            products_batch = Product.objects.filter(id__in=page_ids).only('id', 'name', 'original_category_text', 'category_id')
            
            updates = []

            for p in products_batch:
                # Text na prehľadávanie: Názov + Originálna kategória
                search_text = f"{p.name} {p.original_category_text or ''}".lower()
                
                best_cat_id = None
                highest_priority = -1

                # Prechádzame pravidlá
                for rule in processed_rules:
                    # 1. KONTROLA OUT (Ak nájde, pravidlo neplatí)
                    if any(bad in search_text for bad in rule['out']):
                        continue

                    # 2. KONTROLA MUST (Ak je definované a nenájde ANI JEDNO slovo, pravidlo neplatí)
                    if rule['must']:
                        # "Ak ani jedno zo slov v MUST nie je v texte, tak continue"
                        if not any(good in search_text for good in rule['must']):
                            continue

                    # 3. KONTROLA IN (Ak nájde aspoň jedno, je to kandidát)
                    if any(key in search_text for key in rule['in']):
                        # Porovnanie priorít (Kto má viac bodov, vyhráva)
                        if rule['priority'] > highest_priority:
                            highest_priority = rule['priority']
                            best_cat_id = rule['id']

                # Ak sme našli lepšiu kategóriu, než má produkt teraz
                if best_cat_id and p.category_id != best_cat_id:
                    p.category_id = best_cat_id
                    updates.append(p)

            # Uloženie dávky
            if updates:
                Product.objects.bulk_update(updates, ['category'])
                total_matched += len(updates)
            
            # 🧹 ČISTENIE RAM
            del products_batch
            del updates
            gc.collect()

        self.stdout.write(self.style.SUCCESS(f"🎉 HOTOVO. Celkovo zatriedených {total_matched} produktov."))
        self.stdout.write(f"🏁 Čas trvania: {time.time() - start_time:.2f} s")