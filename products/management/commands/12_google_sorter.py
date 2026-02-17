import csv
import requests
import io
import time
from django.core.management.base import BaseCommand
from products.models import Product, Category
from django.utils.text import slugify

class Command(BaseCommand):
    help = 'CHAIN SORTER 4.0: Buduje strom reťazovým prepojením (L1->L5) a triedi v RAM.'

    def handle(self, *args, **kwargs):
        # ------------------------------------------------------------------
        # 👇 URL TVOJEJ TABUĽKY
        # ------------------------------------------------------------------
        SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSQyXzkFCoyV5w2J36oMvrba9EhjyzrmLyBBk9UkyFpHEVYWbaFMqewAU9N91hDvUR_f-0wDseQgbKD/pub?output=csv"
        
        start_time = time.time()
        self.stdout.write("📊 Sťahujem dáta z Google Sheets...")
        
        try:
            response = requests.get(SHEET_URL)
            response.raise_for_status()
            csv_content = response.content.decode('utf-8')
            # Načítame do zoznamu slovníkov
            rules = list(csv.DictReader(io.StringIO(csv_content)))
            self.stdout.write(f"✅ Načítaných {len(rules)} riadkov.")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Chyba siete: {e}"))
            return

        # ==================================================================
        # FÁZA 1: STROM KATEGÓRIÍ (REŤAZOVÁ LOGIKA)
        # ==================================================================
        self.stdout.write("🌳 FÁZA 1: Budujem strom (L1 -> L2 -> L3 -> L4 -> L5)...")
        
        # Cache: kľúč bude (názov, parent_id) -> hodnota: CategoryObject
        # Tým zabránime duplicitám mien v rôznych vetvách
        cat_cache = {} 

        # Načítame existujúce (ak nejaké ostali po architektovi)
        for c in Category.objects.all():
            cat_cache[(c.name, c.parent_id)] = c

        levels = ['L1', 'L2', 'L3', 'L4', 'L5']

        for row_idx, row in enumerate(rules):
            parent_obj = None # Na začiatku riadku nemáme rodiča (sme na úrovni root)
            
            for level in levels:
                cat_name = row.get(level, '').strip()
                if not cat_name:
                    continue # Ak je bunka prázdna, preskočíme (ale parent_obj ostáva z minula)

                # Kľúč pre cache: (Meno kategórie, ID rodiča)
                # Tým rozlíšime "Oleje" pod "Auto" a "Oleje" pod "Potraviny"
                parent_id = parent_obj.id if parent_obj else None
                cache_key = (cat_name, parent_id)

                if cache_key in cat_cache:
                    # Už ju máme, len sa posunieme hlbšie
                    parent_obj = cat_cache[cache_key]
                else:
                    # Musíme ju vytvoriť
                    # Slug vyrobíme unikátny pridaním rodičovho slugu
                    if parent_obj:
                        new_slug = f"{parent_obj.slug}-{slugify(cat_name)}"[:200]
                    else:
                        new_slug = slugify(cat_name)[:200]

                    # Ošetrenie unikatnosti slugu v DB (keby náhodou)
                    if Category.objects.filter(slug=new_slug).exists():
                         new_slug = f"{new_slug}-{row_idx}"

                    cat, created = Category.objects.get_or_create(
                        name=cat_name,
                        parent=parent_obj,
                        defaults={
                            'slug': new_slug,
                            'is_active': True # Hneď viditeľná!
                        }
                    )
                    # Uložíme do cache a nastavíme ako rodiča pre ďalší level
                    cat_cache[cache_key] = cat
                    parent_obj = cat

        self.stdout.write(self.style.SUCCESS("✅ Strom je postavený. Žiadne siroty."))

        # ==================================================================
        # FÁZA 2: ZBIERANIE CIEĽOV PRE PRODUKTY (Optimalizácia)
        # ==================================================================
        self.stdout.write("🎯 Pripravujem mapu pravidiel...")
        
        # Potrebujeme vedieť, do ktorej kategórie (ID) smeruje každý riadok Excelu.
        # Cieľová kategória je tá POSLEDNÁ vyplnená v riadku.
        
        rule_targets = [] # List tuplov: (in_words, out_words, target_cat_id)

        for row in rules:
            # 1. Nájdi cieľovú kategóriu tohto riadku
            target_cat = None
            parent_obj = None
            
            # Musíme znovu prejsť reťaz, aby sme našli presne to ID, ktoré sme vytvorili v Fáze 1
            for level in levels:
                cat_name = row.get(level, '').strip()
                if not cat_name: continue
                
                parent_id = parent_obj.id if parent_obj else None
                cache_key = (cat_name, parent_id)
                
                if cache_key in cat_cache:
                    target_cat = cat_cache[cache_key]
                    parent_obj = target_cat
            
            if not target_cat: continue

            # 2. Parsuj kľúčové slová
            in_raw = row.get('IN') or row.get('IN (Kľúčové slovo)') or ""
            out_raw = row.get('OUT') or ""
            
            in_words = [w.strip().lower() for w in in_raw.split(',') if w.strip()]
            out_words = [w.strip().lower() for w in out_raw.split(',') if w.strip()]

            if in_words:
                rule_targets.append({
                    'in': in_words,
                    'out': out_words,
                    'id': target_cat.id
                })

        # ==================================================================
        # FÁZA 3: TRIEDENIE PRODUKTOV (IN-MEMORY)
        # ==================================================================
        self.stdout.write("🧠 FÁZA 3: Sťahujem produkty do RAM a triedim...")
        
        # Len potrebné polia = malá spotreba RAM
        products = Product.objects.all().only('id', 'name', 'original_category_text', 'category_id')
        total_products = products.count()
        self.stdout.write(f"📦 Analyzujem {total_products} produktov...")

        updates = {} # {product_id: new_category_id}

        # Iterujeme cez produkty (pretože produktov je veľa, ale pravidiel menej)
        # ALEBO: Iterujeme cez pravidlá?
        # Efektívnejšie je prejsť každý produkt raz a nájsť mu pravidlo. 
        # Alebo prejsť pravidlá a nájsť im produkty.
        # Pri 3500 pravidlách a 50k produktoch je lepšie prejsť pravidlá, lebo python string search je rýchly.

        count = 0
        for p in products:
            count += 1
            if count % 5000 == 0: self.stdout.write(f"   ... {count} / {total_products} ...")

            p_name = p.name.lower()
            p_orig = (p.original_category_text or "").lower()
            
            # Optimalizácia: Hľadáme zhodu. 
            # Toto môže byť pomalé, ak to robíme 50000 x 3500.
            # Zrýchlenie: Väčšina produktov sa chytí na prvé dobré pravidlo.
            
            # Prejdeme pravidlá (v poradí ako sú v Exceli - dôležité pre prioritu!)
            for rule in rule_targets:
                # 1. Check OUT
                if any(bad in p_name for bad in rule['out']):
                    continue
                
                # 2. Check IN
                # Check Name OR Original Category
                found = False
                for w in rule['in']:
                    if w in p_name or w in p_orig:
                        found = True
                        break
                
                if found:
                    # Našli sme zhodu!
                    if p.category_id != rule['id']:
                        updates[p.id] = rule['id']
                    break # BREAK: Produkt je zatriedený, ideme na ďalší produkt (Priorita prvého pravidla)

        # ==================================================================
        # FÁZA 4: HROMADNÝ ZÁPIS
        # ==================================================================
        total_changes = len(updates)
        if total_changes > 0:
            self.stdout.write(self.style.WARNING(f"💾 FÁZA 4: Zapisujem {total_changes} zmien..."))
            
            batch = []
            for pid, cid in updates.items():
                batch.append(Product(id=pid, category_id=cid))
            
            Product.objects.bulk_update(batch, ['category'], batch_size=2000)
            self.stdout.write(self.style.SUCCESS(f"✅ HOTOVO. Aktualizovaných {total_changes} produktov."))
        else:
            self.stdout.write("✨ Žiadne zmeny.")

        self.stdout.write(f"🏁 Čas: {time.time() - start_time:.2f} s")