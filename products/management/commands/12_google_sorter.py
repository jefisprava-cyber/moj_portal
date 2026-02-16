import csv
import requests
import io
import time
from django.core.management.base import BaseCommand
from products.models import Product, Category
from django.db.models import Q
from django.utils.text import slugify

class Command(BaseCommand):
    help = 'GOOGLE SORTER FINAL v3: Optimalizované triedenie s výpisom a viditeľným stromom.'

    def handle(self, *args, **kwargs):
        # ==============================================================================
        # 👇👇👇 VLOŽ ODKAZ Z GOOGLE SHEETS (PUBLISH TO WEB -> CSV) 👇👇👇
        # ==============================================================================
        SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSQyXzkFCoyV5w2J36oMvrba9EhjyzrmLyBBk9UkyFpHEVYWbaFMqewAU9N91hDvUR_f-0wDseQgbKD/pub?output=csv"
        # ==============================================================================

        start_time = time.time()
        self.stdout.write("📊 Sťahujem pravidlá z Google Sheets...")
        
        try:
            response = requests.get(SHEET_URL)
            response.raise_for_status()
            csv_content = response.content.decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(csv_content))
            rules = list(csv_reader)
            self.stdout.write(f"✅ Načítaných {len(rules)} riadkov z tabuľky.")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Chyba pri sťahovaní: {e}"))
            return

        # ------------------------------------------------------------------
        # FÁZA 1: BUDOVANIE STROMU KATEGÓRIÍ (vrátane L4 a L5)
        # ------------------------------------------------------------------
        self.stdout.write("🌳 FÁZA 1: Budujem strom kategórií (L1-L5)...")
        
        # Mapa: Názov kategórie -> Objekt kategórie (pre rýchlosť)
        category_map = {}

        # Načítame existujúce kategórie do pamäte
        for cat in Category.objects.all():
            category_map[cat.name] = cat

        for row in rules:
            # 1. Zistíme NÁZOV (L1 -> L5)
            cat_name = ""
            if row.get('L1', '').strip(): cat_name = row['L1'].strip()
            elif row.get('L2', '').strip(): cat_name = row['L2'].strip()
            elif row.get('L3', '').strip(): cat_name = row['L3'].strip()
            elif row.get('L4', '').strip(): cat_name = row['L4'].strip()
            elif row.get('L5', '').strip(): cat_name = row['L5'].strip()
            
            if not cat_name: continue

            # 2. Zistíme RODIČA
            parent_name_csv = row.get('RODIC', '').strip()
            parent_obj = None

            if parent_name_csv:
                parent_obj = category_map.get(parent_name_csv)
                
                # Fallback: ak rodič neexistuje, vytvoríme ho
                if not parent_obj:
                    parent_slug = slugify(parent_name_csv)[:50]
                    parent_obj, _ = Category.objects.get_or_create(
                        name=parent_name_csv,
                        defaults={
                            'slug': parent_slug, 
                            'is_active': True # Rodič musí byť viditeľný
                        }
                    )
                    category_map[parent_name_csv] = parent_obj

            # 3. Vytvoríme/Aktualizujeme kategóriu
            base_slug = slugify(cat_name)[:50]
            my_slug = f"{parent_obj.slug}-{base_slug}"[:200] if parent_obj else base_slug

            # DÔLEŽITÉ: is_active=True znamená, že kategória bude hneď viditeľná na webe!
            category, created = Category.objects.update_or_create(
                name=cat_name,
                defaults={
                    'slug': my_slug,
                    'parent': parent_obj,
                    'is_active': True 
                }
            )
            category_map[cat_name] = category

        self.stdout.write(self.style.SUCCESS("✅ Strom postavený (všetky kategórie sú nastavené ako viditeľné)."))

        # ------------------------------------------------------------------
        # FÁZA 2: TRIEDENIE PRODUKTOV
        # ------------------------------------------------------------------
        self.stdout.write("🌪️  FÁZA 2: Triedim produkty podľa kľúčových slov...")

        total_updated = 0
        total_rules = len(rules)

        # Používame enumerate, aby sme videli číslo riadku
        for i, row in enumerate(rules, 1):
            
            # --- VÝPIS PRIEBEHU (aby si videl, že to nezamrzlo) ---
            if i % 20 == 0:
                self.stdout.write(f"⏳ Spracovávam pravidlo {i}/{total_rules}...")

            # Znova zistíme cieľovú kategóriu
            cat_name = ""
            if row.get('L1', '').strip(): cat_name = row['L1'].strip()
            elif row.get('L2', '').strip(): cat_name = row['L2'].strip()
            elif row.get('L3', '').strip(): cat_name = row['L3'].strip()
            elif row.get('L4', '').strip(): cat_name = row['L4'].strip()
            elif row.get('L5', '').strip(): cat_name = row['L5'].strip()
            
            if not cat_name: continue

            # Rýchly lookup v mape (nevoláme DB)
            target_cat = category_map.get(cat_name)
            if not target_cat: continue

            # Načítanie kľúčových slov
            keywords_in_raw = row.get('IN', '') or row.get('IN (Kľúčové slovo)', '')
            keywords_out_raw = row.get('OUT', '')

            if not keywords_in_raw: continue

            # Rozdelenie slov
            keywords_in = [w.strip() for w in keywords_in_raw.split(',') if w.strip()]
            keywords_out = [w.strip() for w in keywords_out_raw.split(',') if w.strip()]

            if not keywords_in: continue

            # --- TVORBA QUERY (Optimalizovaná) ---
            
            # 1. IN podmienka (Názov OR Pôvodná kategória)
            query_in = Q()
            for kw in keywords_in:
                # Ak máš nastavené db_index=True v models.py, toto bude rýchle
                query_in |= Q(name__icontains=kw) | Q(original_category_text__icontains=kw)

            # 2. OUT podmienka (Vylučovacie slová)
            query_out = Q()
            for kw in keywords_out:
                query_out |= Q(name__icontains=kw)

            # 3. UPDATE
            # Vyberieme produkty, ktoré spĺňajú IN, nespĺňajú OUT a nie sú už tam
            products_to_update = Product.objects.filter(query_in).exclude(query_out).exclude(category=target_cat)
            
            count = products_to_update.update(category=target_cat)
            
            if count > 0:
                total_updated += count

        end_time = time.time()
        duration = end_time - start_time

        self.stdout.write(self.style.SUCCESS(f"🏁 HOTOVO za {duration:.2f} sekúnd."))
        self.stdout.write(self.style.SUCCESS(f"📦 Celkovo presunutých produktov: {total_updated}"))
        
        # ------------------------------------------------------------------
        # FÁZA 3: FINÁLNE ZOBRAZENIE
        # ------------------------------------------------------------------
        # Pôvodný kód tu skrýval prázdne kategórie. 
        # Teraz to vynecháme, aby si videl celú novú štruktúru na webe.
        
        # self.stdout.write("🧹 Skrývanie prázdnych kategórií je vypnuté (VIDÍŠ VŠETKO).")
        
        # Pre istotu ešte raz potvrdíme, že všetko je aktívne
        # Category.objects.update(is_active=True) 
        
        visible_count = Category.objects.filter(is_active=True).count()
        self.stdout.write(self.style.SUCCESS(f"✅ Na webe je teraz viditeľných {visible_count} kategórií."))