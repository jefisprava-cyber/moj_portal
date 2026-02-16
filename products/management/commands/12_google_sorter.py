import csv
import requests
import io
import time
from django.core.management.base import BaseCommand
from products.models import Product, Category
from django.db.models import Q
from django.utils.text import slugify

class Command(BaseCommand):
    help = 'GOOGLE SORTER TURBO BULK: Načíta všetky zmeny do pamäte a zapíše ich naraz.'

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
        # FÁZA 1: BUDOVANIE STROMU KATEGÓRIÍ (L1-L5)
        # ------------------------------------------------------------------
        self.stdout.write("🌳 FÁZA 1: Budujem strom kategórií...")
        
        category_map = {} # Názov -> Objekt
        category_id_map = {} # Názov -> ID (pre fázu 2)

        # Načítame existujúce
        for cat in Category.objects.all():
            category_map[cat.name] = cat
            category_id_map[cat.name] = cat.id

        for row in rules:
            # 1. Zistíme NÁZOV
            cat_name = ""
            if row.get('L5', '').strip(): cat_name = row['L5'].strip()
            elif row.get('L4', '').strip(): cat_name = row['L4'].strip()
            elif row.get('L3', '').strip(): cat_name = row['L3'].strip()
            elif row.get('L2', '').strip(): cat_name = row['L2'].strip()
            elif row.get('L1', '').strip(): cat_name = row['L1'].strip()
            
            if not cat_name: continue

            # 2. Zistíme RODIČA
            parent_name_csv = row.get('RODIC', '').strip()
            parent_obj = None

            if parent_name_csv:
                parent_obj = category_map.get(parent_name_csv)
                if not parent_obj:
                    parent_slug = slugify(parent_name_csv)[:50]
                    # Rodiča vytvoríme hneď ako AKTÍVNEHO
                    parent_obj, _ = Category.objects.get_or_create(
                        name=parent_name_csv,
                        defaults={'slug': parent_slug, 'is_active': True}
                    )
                    category_map[parent_name_csv] = parent_obj
                    category_id_map[parent_name_csv] = parent_obj.id

            # 3. Vytvoríme/Update kategórie
            base_slug = slugify(cat_name)[:50]
            my_slug = f"{parent_obj.slug}-{base_slug}"[:200] if parent_obj else base_slug

            # Taktiež kategóriu vytvárame hneď ako AKTÍVNU
            category, created = Category.objects.update_or_create(
                name=cat_name,
                defaults={
                    'slug': my_slug,
                    'parent': parent_obj,
                    'is_active': True
                }
            )
            category_map[cat_name] = category
            category_id_map[cat_name] = category.id

        self.stdout.write(self.style.SUCCESS("✅ Strom postavený."))

        # ------------------------------------------------------------------
        # FÁZA 2: PRÍPRAVA DÁT V PAMÄTI (RAM)
        # ------------------------------------------------------------------
        self.stdout.write("🧠 FÁZA 2: Analyzujem produkty (Bulk Logic)...")

        # Slovník: { product_id : new_category_id }
        product_updates_map = {}
        
        total_rules = len(rules)

        for i, row in enumerate(rules, 1):
            if i % 50 == 0:
                self.stdout.write(f"⏳ Analyzujem pravidlo {i}/{total_rules}...")

            # Zistenie cieľovej kategórie
            cat_name = ""
            if row.get('L1', '').strip(): cat_name = row['L1'].strip()
            elif row.get('L2', '').strip(): cat_name = row['L2'].strip()
            elif row.get('L3', '').strip(): cat_name = row['L3'].strip()
            elif row.get('L4', '').strip(): cat_name = row['L4'].strip()
            elif row.get('L5', '').strip(): cat_name = row['L5'].strip()
            
            if not cat_name: continue
            
            target_cat_id = category_id_map.get(cat_name)
            if not target_cat_id: continue

            # Kľúčové slová
            keywords_in_raw = row.get('IN', '') or row.get('IN (Kľúčové slovo)', '')
            keywords_out_raw = row.get('OUT', '')

            if not keywords_in_raw: continue

            keywords_in = [w.strip() for w in keywords_in_raw.split(',') if w.strip()]
            keywords_out = [w.strip() for w in keywords_out_raw.split(',') if w.strip()]

            if not keywords_in: continue

            # --- RÝCHLE ČÍTANIE (READ ONLY) ---
            
            query_in = Q()
            for kw in keywords_in:
                query_in |= Q(name__icontains=kw) | Q(original_category_text__icontains=kw)

            query_out = Q()
            for kw in keywords_out:
                query_out |= Q(name__icontains=kw)

            # Získame len IDčká produktov, ktoré sedia na pravidlo
            matched_ids = Product.objects.filter(query_in).exclude(query_out).exclude(category_id=target_cat_id).values_list('id', flat=True)

            # Uložíme do mapy v pamäti
            for pid in matched_ids:
                product_updates_map[pid] = target_cat_id

        # ------------------------------------------------------------------
        # FÁZA 3: HROMADNÝ ZÁPIS (BULK UPDATE)
        # ------------------------------------------------------------------
        count_to_update = len(product_updates_map)
        self.stdout.write(self.style.WARNING(f"💾 FÁZA 3: Začínam hromadný zápis {count_to_update} produktov..."))

        if count_to_update > 0:
            # Pripravíme objekty na update
            batch = []
            for pid, new_cat_id in product_updates_map.items():
                batch.append(Product(id=pid, category_id=new_cat_id))
            
            # Django Bulk Update - toto je ten zázrak
            # batch_size=1000 znamená, že to pošle do DB po 1000 kusoch
            Product.objects.bulk_update(batch, ['category'], batch_size=1000)
            
            self.stdout.write(self.style.SUCCESS(f"✅ Úspešne presunutých {count_to_update} produktov."))
        else:
            self.stdout.write("✨ Žiadne zmeny neboli potrebné.")

        end_time = time.time()
        duration = end_time - start_time
        self.stdout.write(self.style.SUCCESS(f"🏁 KOMPLETNE HOTOVO za {duration:.2f} sekúnd."))

        # Finálny check viditeľnosti
        # Všetky kategórie by mali byť viditeľné, lebo sme ich tak vytvorili vo FÁZE 1
        visible = Category.objects.filter(is_active=True).count()
        self.stdout.write(f"👁️  Viditeľných kategórií: {visible}")