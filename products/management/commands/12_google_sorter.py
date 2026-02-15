import csv
import requests
import io
from django.core.management.base import BaseCommand
from products.models import Product, Category
from django.db.models import Q
from django.utils.text import slugify

class Command(BaseCommand):
    help = 'GOOGLE SORTER FINAL: Stavia strom (L1-L5) a triedi (Názov + Pôvodná kategória).'

    def handle(self, *args, **kwargs):
        # ==============================================================================
        # 👇👇👇 SEM VLOŽ TVOJ ODKAZ Z GOOGLE SHEETS (PUBLISH TO WEB -> CSV) 👇👇👇
        # ==============================================================================
        SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSQyXzkFCoyV5w2J36oMvrba9EhjyzrmLyBBk9UkyFpHEVYWbaFMqewAU9N91hDvUR_f-0wDseQgbKD/pub?output=csv"
        # ==============================================================================

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
        self.stdout.write("🌳 FÁZA 1: Budujem strom kategórií (vrátane L4 a L5)...")
        
        # Mapa: ID z tabuľky -> Reálny objekt Category v databáze
        # ID 0 je "koreň" (None)
        parent_map = {'0': None} 

        # Zoradíme podľa ID, aby sme vždy najprv vytvorili rodiča, až potom dieťa
        # Predpokladáme, že v tabuľke má rodič vždy menšie ID ako dieťa, alebo sú zoradené
        # Ak nie sú, bolo by treba viac prechodov. Pre istotu triedime podľa ID (ak je numerické).
        try:
            rules.sort(key=lambda x: int(x['ID']) if x['ID'].isdigit() else 999999)
        except:
            pass # Ak ID nie sú čísla, necháme pôvodné poradie

        for row in rules:
            # 1. Zistíme NÁZOV (Prechádzame L1 -> L5)
            cat_name = ""
            if row.get('L1', '').strip(): cat_name = row['L1'].strip()
            elif row.get('L2', '').strip(): cat_name = row['L2'].strip()
            elif row.get('L3', '').strip(): cat_name = row['L3'].strip()
            elif row.get('L4', '').strip(): cat_name = row['L4'].strip() # <--- NOVÉ
            elif row.get('L5', '').strip(): cat_name = row['L5'].strip() # <--- NOVÉ
            
            if not cat_name:
                continue

            # 2. Zistíme RODIČA
            parent_id_csv = row.get('RODIC', '0').strip()
            parent_obj = parent_map.get(parent_id_csv)

            # 3. Vytvoríme alebo získame kategóriu
            my_slug = slugify(cat_name)
            # Unikátny slug pre istotu (ak by boli rovnaké názvy v rôznych vetvách)
            if parent_obj:
                my_slug = f"{parent_obj.slug}-{my_slug}"[:200] 

            category, created = Category.objects.update_or_create(
                slug=my_slug,
                defaults={
                    'name': cat_name,
                    'parent': parent_obj,
                    'is_active': False # Zatiaľ skryté, aktivujeme na konci ak má produkty
                }
            )

            # 4. Uložíme si mapping pre deti
            my_id_csv = row.get('ID', '').strip()
            if my_id_csv:
                parent_map[my_id_csv] = category

        self.stdout.write(self.style.SUCCESS("✅ Strom postavený."))

        # ------------------------------------------------------------------
        # FÁZA 2: TRIEDENIE PRODUKTOV
        # ------------------------------------------------------------------
        self.stdout.write("🌪️  FÁZA 2: Triedim produkty podľa kľúčových slov...")

        total_updated = 0

        for row in rules:
            # Znova zistíme názov kategórie, aby sme vedeli, kam hádzať produkty
            cat_name = ""
            if row.get('L1', '').strip(): cat_name = row['L1'].strip()
            elif row.get('L2', '').strip(): cat_name = row['L2'].strip()
            elif row.get('L3', '').strip(): cat_name = row['L3'].strip()
            elif row.get('L4', '').strip(): cat_name = row['L4'].strip() # <--- NOVÉ
            elif row.get('L5', '').strip(): cat_name = row['L5'].strip() # <--- NOVÉ
            
            if not cat_name: continue

            # Nájdi ID tejto kategórie v našej mape
            my_id_csv = row.get('ID', '').strip()
            target_cat = parent_map.get(my_id_csv)

            if not target_cat:
                continue

            # Načítanie kľúčových slov
            keywords_in_raw = row.get('KLUCOVE_SLOVA_IN', '')
            keywords_out_raw = row.get('KLUCOVE_SLOVA_OUT', '')

            if not keywords_in_raw:
                continue

            # Spracovanie slov (oddelené čiarkou)
            keywords_in = [w.strip() for w in keywords_in_raw.split(',') if w.strip()]
            keywords_out = [w.strip() for w in keywords_out_raw.split(',') if w.strip()]

            if not keywords_in:
                continue

            # --- TVORBA QUERY ---
            # 1. Hľadáme v Názve
            query_in_name = Q()
            for kw in keywords_in: query_in_name |= Q(name__icontains=kw)
            
            # 2. Hľadáme v Pôvodnej kategórii (Heureka cesta)
            query_in_orig = Q()
            for kw in keywords_in: query_in_orig |= Q(original_category_text__icontains=kw)

            # Spojíme (OR) - stačí ak sa slovo nájde v názve ALEBO v pôvodnej ceste
            final_in_query = (query_in_name | query_in_orig)

            # 3. Vylučovacie slová (MUSIA platiť pre názov)
            query_out = Q()
            for kw in keywords_out: query_out |= Q(name__icontains=kw)

            # Update
            products_to_update = Product.objects.filter(final_in_query).exclude(query_out)
            count = products_to_update.update(category=target_cat)
            
            if count > 0:
                total_updated += count
                # Voliteľné: Výpis pre kontrolu (spomaľuje pri tisíckach)
                # self.stdout.write(f"   -> {cat_name}: +{count} produktov")

        self.stdout.write(self.style.SUCCESS(f"🏁 HOTOVO. Zatriedených {total_updated} produktov."))
        
        # ------------------------------------------------------------------
        # FÁZA 3: AKTIVÁCIA (Len tie, čo majú produkty)
        # ------------------------------------------------------------------
        self.stdout.write("💡 Aktivujem kategórie, ktoré majú produkty...")
        
        # Reset všetkých na False (aby sme skryli prázdne)
        # Pozor: Toto skryje aj kategórie z Precision Sortera, ak nemajú produkty.
        # Ak chceš kombinovať, možno tento reset vynechaj alebo uprav.
        Category.objects.update(is_active=False)

        # Nájdi kategórie, ktoré majú aspoň 1 produkt
        active_ids = Product.objects.values_list('category_id', flat=True).distinct()
        
        # Aktivuj ich
        Category.objects.filter(id__in=active_ids).update(is_active=True)

        # Aktivuj aj ich rodičov (aby sa dalo preklikať)
        # Toto je jednoduchý cyklus, pre hlboký strom (L5) treba možno opakovať
        for i in range(5): # 5x prejdeme strom hore, aby sme chytili L5->L4->L3->L2->L1
            parents = Category.objects.filter(children__is_active=True).distinct()
            parents.update(is_active=True)

        visible_count = Category.objects.filter(is_active=True).count()
        self.stdout.write(self.style.SUCCESS(f"✅ Vo finále je aktívnych {visible_count} kategórií."))