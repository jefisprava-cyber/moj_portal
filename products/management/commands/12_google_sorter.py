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
        # 👇👇👇 VLOŽ ODKAZ Z GOOGLE SHEETS (PUBLISH TO WEB -> CSV) 👇👇👇
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
        
        # Mapa: Názov kategórie -> Objekt kategórie (pre rýchle vyhľadávanie rodičov)
        # Používame slovník { "Názov": CategoryObject }
        category_map = {}

        # Najprv si načítame existujúce kategórie do pamäte, aby sme nerobili zbytočné queries
        for cat in Category.objects.all():
            category_map[cat.name] = cat

        for row in rules:
            # 1. Zistíme NÁZOV (Prechádzame L1 -> L5)
            cat_name = ""
            level = 0
            if row.get('L1', '').strip(): 
                cat_name = row['L1'].strip()
                level = 1
            elif row.get('L2', '').strip(): 
                cat_name = row['L2'].strip()
                level = 2
            elif row.get('L3', '').strip(): 
                cat_name = row['L3'].strip()
                level = 3
            elif row.get('L4', '').strip(): 
                cat_name = row['L4'].strip() # <--- NOVÉ
                level = 4
            elif row.get('L5', '').strip(): 
                cat_name = row['L5'].strip() # <--- NOVÉ
                level = 5
            
            if not cat_name:
                continue

            # 2. Zistíme RODIČA (zo stĺpca RODIC)
            parent_name_csv = row.get('RODIC', '').strip()
            parent_obj = None

            if parent_name_csv:
                # Skúsime nájsť rodiča v našej mape
                parent_obj = category_map.get(parent_name_csv)
                
                # Ak rodič v mape nie je (čo by sa nemalo stať, ak je tabuľka dobre zoradená),
                # skúsime ho vytvoriť "na slepo" alebo ho nájsť v DB.
                if not parent_obj:
                    # Fallback: vytvoríme rodiča, ak neexistuje
                    parent_slug = slugify(parent_name_csv)[:50]
                    parent_obj, _ = Category.objects.get_or_create(
                        name=parent_name_csv,
                        defaults={'slug': parent_slug, 'is_active': False}
                    )
                    category_map[parent_name_csv] = parent_obj

            # 3. Vytvoríme alebo získame kategóriu
            base_slug = slugify(cat_name)[:50]
            # Unikátny slug pre istotu
            if parent_obj:
                my_slug = f"{parent_obj.slug}-{base_slug}"[:200]
            else:
                my_slug = base_slug

            # Update or Create
            category, created = Category.objects.update_or_create(
                name=cat_name,
                defaults={
                    'slug': my_slug,
                    'parent': parent_obj,
                    'is_active': False 
                }
            )
            
            # Uložíme do mapy pre ďalšie použitie (ako rodiča pre ďalšie levely)
            category_map[cat_name] = category

        self.stdout.write(self.style.SUCCESS("✅ Strom postavený."))

        # ------------------------------------------------------------------
        # FÁZA 2: TRIEDENIE PRODUKTOV
        # ------------------------------------------------------------------
        self.stdout.write("🌪️  FÁZA 2: Triedim produkty podľa kľúčových slov...")

        total_updated = 0

        for row in rules:
            # Znova zistíme názov kategórie
            cat_name = ""
            if row.get('L1', '').strip(): cat_name = row['L1'].strip()
            elif row.get('L2', '').strip(): cat_name = row['L2'].strip()
            elif row.get('L3', '').strip(): cat_name = row['L3'].strip()
            elif row.get('L4', '').strip(): cat_name = row['L4'].strip() # <--- NOVÉ
            elif row.get('L5', '').strip(): cat_name = row['L5'].strip() # <--- NOVÉ
            
            if not cat_name: continue

            # Nájdi objekt kategórie
            target_cat = category_map.get(cat_name)

            if not target_cat:
                continue

            # Načítanie kľúčových slov
            keywords_in_raw = row.get('IN', '') # V tabuľke sa stĺpec volá "IN (Kľúčové slovo)" alebo len "IN"? Uprav podľa CSV.
            keywords_out_raw = row.get('OUT', '')

            # Fallback ak sa stlpec vola inak
            if not keywords_in_raw: keywords_in_raw = row.get('IN (Kľúčové slovo)', '')

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

            # Update - neprepíše ak už je správne
            products_to_update = Product.objects.filter(final_in_query).exclude(query_out).exclude(category=target_cat)
            count = products_to_update.update(category=target_cat)
            
            if count > 0:
                total_updated += count

        self.stdout.write(self.style.SUCCESS(f"🏁 HOTOVO. Zatriedených {total_updated} produktov."))
        
        # ------------------------------------------------------------------
        # FÁZA 3: AKTIVÁCIA (Len tie, čo majú produkty)
        # ------------------------------------------------------------------
        self.stdout.write("💡 Aktivujem kategórie, ktoré majú produkty...")
        
        # Skryjeme všetko okrem koreňových
        Category.objects.update(is_active=False)

        # Nájdi kategórie, ktoré majú aspoň 1 produkt
        active_ids = Product.objects.values_list('category_id', flat=True).distinct()
        
        # Aktivuj ich
        Category.objects.filter(id__in=active_ids).update(is_active=True)

        # Aktivuj rodičov rekurzívne
        changed = True
        while changed:
            parents = Category.objects.filter(is_active=False, children__is_active=True)
            if parents.exists():
                parents.update(is_active=True)
            else:
                changed = False

        visible_count = Category.objects.filter(is_active=True).count()
        self.stdout.write(self.style.SUCCESS(f"✅ Vo finále je aktívnych {visible_count} kategórií."))