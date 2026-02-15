import csv
import requests
import io
from django.core.management.base import BaseCommand
from products.models import Product, Category
from django.db.models import Q
from django.utils.text import slugify

class Command(BaseCommand):
    help = 'GOOGLE SORTER FINAL: Stavia strom a triedi (Názov + Pôvodná kategória).'

    def handle(self, *args, **kwargs):
        # ==============================================================================
        # 👇👇👇 SEM VLOŽ TVOJ ODKAZ Z GOOGLE SHEETS (PUBLISH TO WEB -> CSV) 👇👇👇
        # ==============================================================================
        SHEET_URL = "SEM_VLOZ_TVhttps://docs.google.com/spreadsheets/d/e/2PACX-1vSQyXzkFCoyV5w2J36oMvrba9EhjyzrmLyBBk9UkyFpHEVYWbaFMqewAU9N91hDvUR_f-0wDseQgbKD/pub?output=csvOJ_DLHY_ODKAZ_Z_GOOGLE_SHEETS"
        # ==============================================================================

        self.stdout.write("📊 Sťahujem pravidlá z Google Sheets...")
        
        try:
            response = requests.get(SHEET_URL)
            response.raise_for_status()
            csv_content = response.content.decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(csv_content))
            rules = list(csv_reader)
            self.stdout.write(f"✅ Načítaných {len(rules)} riadkov.")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Chyba: {e}"))
            return

        # ---------------------------------------------------------
        # FÁZA 1: STAVANIE STROMU
        # ---------------------------------------------------------
        self.stdout.write("🏗️  Aktualizujem strom kategórií...")
        category_cache = {}

        for row in rules:
            # 1. Zistíme NÁZOV (L1, L2, L3)
            cat_name = ""
            if row.get('L1', '').strip(): cat_name = row['L1'].strip()
            elif row.get('L2', '').strip(): cat_name = row['L2'].strip()
            elif row.get('L3', '').strip(): cat_name = row['L3'].strip()
            
            if not cat_name: continue

            # 2. Zistíme RODIČA
            parent_name = row.get('RODIC', '').strip()
            parent_obj = None

            if parent_name:
                if parent_name in category_cache:
                    parent_obj = category_cache[parent_name]
                else:
                    parent_obj, _ = Category.objects.get_or_create(
                        name=parent_name,
                        defaults={'slug': slugify(parent_name)[:50], 'is_active': False}
                    )
                    category_cache[parent_name] = parent_obj

            # 3. Vytvoríme/Aktualizujeme KATEGÓRIU
            base_slug = slugify(cat_name)[:50]
            if parent_obj:
                final_slug = slugify(f"{parent_obj.slug}-{base_slug}")[:80]
            else:
                final_slug = base_slug

            cat_obj, created = Category.objects.get_or_create(
                name=cat_name,
                defaults={'slug': final_slug, 'parent': parent_obj, 'is_active': False}
            )

            if not created and cat_obj.parent != parent_obj:
                cat_obj.parent = parent_obj
                cat_obj.save()
            
            category_cache[cat_name] = cat_obj

        self.stdout.write("✅ Strom postavený.")

        # ---------------------------------------------------------
        # FÁZA 2: TRIEDENIE PRODUKTOV (Dual Check)
        # ---------------------------------------------------------
        self.stdout.write("🚀 Triedim produkty...")
        total_updated = 0

        for row in rules:
            cat_name = ""
            if row.get('L1', '').strip(): cat_name = row['L1'].strip()
            elif row.get('L2', '').strip(): cat_name = row['L2'].strip()
            elif row.get('L3', '').strip(): cat_name = row['L3'].strip()
            
            if not cat_name: continue

            target_cat = category_cache.get(cat_name)
            keywords_in = [k.strip().lower() for k in row.get('IN', '').split(',') if k.strip()]
            keywords_out = [k.strip().lower() for k in row.get('OUT', '').split(',') if k.strip()]

            if not target_cat or not keywords_in: continue

            # --- DUAL CHECK LOGIKA ---
            # 1. Hľadáme v Názve
            query_in_name = Q()
            for kw in keywords_in: query_in_name |= Q(name__icontains=kw)
            
            # 2. Hľadáme v Pôvodnej kategórii (Heureka cesta)
            query_in_orig = Q()
            for kw in keywords_in: query_in_orig |= Q(original_category_text__icontains=kw)

            # Spojíme (OR)
            final_in_query = (query_in_name | query_in_orig)

            # 3. Vylučovacie slová (MUSIA platiť pre názov)
            query_out = Q()
            for kw in keywords_out: query_out |= Q(name__icontains=kw)

            # Update
            products_to_update = Product.objects.filter(final_in_query).exclude(query_out)
            count = products_to_update.update(category=target_cat)
            
            if count > 0:
                total_updated += count

        self.stdout.write(self.style.SUCCESS(f"🏁 HOTOVO. Zatriedených {total_updated} produktov."))
        
        # Aktivátor
        Category.objects.update(is_active=False)
        active_ids = Product.objects.values_list('category_id', flat=True).distinct()
        Category.objects.filter(id__in=active_ids).exclude(slug__icontains="nezaradene").update(is_active=True)
        
        changed = True
        while changed:
            parents = Category.objects.filter(is_active=False, children__is_active=True)
            if parents.exists(): parents.update(is_active=True)
            else: changed = False