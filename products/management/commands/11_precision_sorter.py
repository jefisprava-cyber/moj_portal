import sys
from django.core.management.base import BaseCommand
from products.models import Category, Product
from django.db.models import Count, Q
from django.db import transaction

class Command(BaseCommand):
    help = 'PRECISION SORTER v6.0: ULTIMATE EDITION - Kompletné pravidlá pre celý e-shop.'

    def handle(self, *args, **kwargs):
        self.stdout.write("🦁 PRECISION SORTER: Štartujem masívnu analýzu produktov...")

        # =========================================================================
        # 🧠 VEĽKÁ MAPA PRAVIDIEL (KOMPLETNÁ SADA PRE CELÝ STROM)
        # =========================================================================
        RULES = {
            # ---------------------------------------------------------------------
            # 🚗 MOTORISTICKÝ SVET
            # ---------------------------------------------------------------------
            'Pneumatiky': {
                'in': ['pneumatika', 'pneu', 'letné', 'zimné', 'celoročné', 'matador', 'barum', 'michelin', 'bridgestone', 'hankook', 'nokian', 'continental', 'pirelli'],
                'out': ['disk', 'disky', 'elektrón', 'ráfik', 'puklice', 'reťaze', 'nosič', 'snímač', 'ventil', 'oprava', 'stojan', 'tekuté', 'kompresor']
            },
            'Disky a ráfiky': {
                'in': ['disk', 'disky', 'elektróny', 'alu disk', 'plechový disk', 'dotz', 'dezent', 'aez', 'enzo', 'stredové krytky'],
                'out': ['pneumatika', 'pneu', 'čistič', 'stojan', 'puklice']
            },
            'Autobatérie': {
                'in': ['autobatéria', 'akumulátor do auta', 'varta', 'exide', 'bosch s4', 'bosch s5', 'start-stop'],
                'out': ['nabíjačka', 'tester', 'svorka', 'štartovací zdroj']
            },
            'Motorové oleje': {
                'in': ['motorový olej', '5w-30', '5w-40', '10w-40', 'castrol edge', 'shell helix', 'mobil 1', 'total quartz', 'valvoline'],
                'out': ['filter', 'aditívum', 'preplach']
            },
            'Autokozmetika': {
                'in': ['autokozmetika', 'šampón na auto', 'vosk na auto', 'čistič diskov', 'oživovač pneu', 'coyote', 'sheron', 'sonax', 'tekuté stierače'],
                'out': []
            },
            'Strešné nosiče': {
                'in': ['strešný nosič', 'strešný box', 'nosič lyží', 'nosič bicyklov na strechu', 'thule'],
                'out': []
            },

            # ---------------------------------------------------------------------
            # 🪑 NÁBYTOK A BÝVANIE (Interiér)
            # ---------------------------------------------------------------------
            'Stoličky': {
                'in': ['stolička', 'jedálenská stolička', 'barová stolička', 'taburet', 'stoličky', 'sedák'],
                'out': ['kancelárske', 'herné', 'kempingová', 'rybárska', 'do auta', 'kŕmenie', 'záhradná']
            },
            'Stoly a stolíky': {
                'in': ['stôl', 'stolík', 'jedálenský stôl', 'konferenčný stolík', 'nočný stolík', 'písací stôl', 'toaletný stolík'],
                'out': ['stolný', 'tenis', 'futbal', 'brúsny', 'záhradný']
            },
            'Komody': {
                'in': ['komoda', 'príborník', 'skrinka so zásuvkami', 'šuplíková skrinka'],
                'out': ['prebaľovacia']
            },
            'Skrine': {
                'in': ['skrinka', 'skriňa', 'šatníková skriňa', 'policová skriňa', 'vitrína', 'regál', 'knižnica'],
                'out': ['potravinová', 'elektro', 'pc skriňa', 'záhradná']
            },
            'Predsieňové steny': {
                'in': ['predsieňová stena', 'vešiaková stena', 'botník', 'šatníkový panel', 'vešiak do predsiene'],
                'out': []
            },
            'Postele': {
                'in': ['posteľ', 'manželská posteľ', 'váľanda', 'jednolôžko', 'poschodová posteľ', 'boxspring', 'čalúnená posteľ'],
                'out': ['obliečky', 'plachta', 'matrac', 'rošt', 'peleš', 'domček', 'nafukovacia']
            },
            'Matrace': {
                'in': ['matrac', 'penový matrac', 'pružinový matrac', 'vrchný matrac', 'topper', 'kokosový matrac'],
                'out': ['nafukovací', 'do vody', 'skákací', 'camping', 'chránič']
            },
            'Sedacie súpravy': {
                'in': ['sedačka', 'sedacia súprava', 'pohovka', 'gauč', 'kreslo', 'ušiak', 'leňoška'],
                'out': ['do auta', 'kancelárske', 'nafukovacie', 'detské', 'záhradné']
            },
            'Kancelárske kreslá': {
                'in': ['kancelárske kreslo', 'kancelárska stolička', 'otočné kreslo', 'ergonomická stolička'],
                'out': ['podložka', 'kolieska']
            },
            'Herné kreslá': {
                'in': ['herné kreslo', 'gaming chair', 'kreslo pre hráčov', 'dxracer', 'czc'],
                'out': []
            },
            'Osvetlenie': {
                'in': ['lampa', 'svietidlo', 'luster', 'stropné svetlo', 'stojacia lampa', 'stolná lampa', 'bodové svetlo'],
                'out': ['autožiarovka', 'baterka', 'čelovka']
            },
             'Bytový textil': {
                'in': ['vankúš', 'paplón', 'prikrývka', 'deka', 'obliečky', 'plachta', 'uterák', 'osuška', 'záves', 'záclona', 'koberec', 'behúň'],
                'out': ['kojenecký', 'do kočíka', 'do auta']
            },

            # ---------------------------------------------------------------------
            # 📱 TECHNOLÓGIE A GADGETS
            # ---------------------------------------------------------------------
            'Mobilné telefóny': {
                'in': ['smartphone', 'mobilný telefón', 'iphone', 'samsung galaxy', 'xiaomi redmi', 'realme', 'motorola', 'honor', 'oneplus', 'google pixel'],
                'out': ['puzdro', 'obal', 'kryt', 'sklo', 'fólia', 'držiak', 'nabíjačka', 'kábel', 'remienok', 'dummy', 'maketa']
            },
            'Puzdrá na mobilné telefóny': {
                'in': ['puzdro na mobil', 'obal na mobil', 'kryt na', 'flipové puzdro', 'silikónové puzdro', 'zadný kryt', 'case', 'cover', 'kožené puzdro'],
                'out': []
            },
            'Ochranné fólie pre mobilné telefóny': {
                'in': ['ochranné sklo', 'tvrdené sklo', 'tempered glass', 'ochranná fólia na mobil', 'glass', 'screen protector'],
                'out': ['hodinky', 'tablet', 'ipad', 'fotoaparát']
            },
            'Inteligentné hodinky': {
                'in': ['smart watch', 'inteligentné hodinky', 'apple watch', 'garmin fenix', 'garmin venu', 'galaxy watch', 'amazfit', 'huawei watch', 'fitbit'],
                'out': ['remienok', 'náramok', 'fólia', 'nabíjačka', 'ochranné sklo']
            },
            'Fitness náramky': {
                'in': ['fitness náramok', 'smart band', 'mi band', 'honor band'],
                'out': ['remienok', 'nabíjačka']
            },
            'Herné konzoly': {
                'in': ['playstation 5', 'ps5', 'xbox series', 'nintendo switch', 'steam deck', 'xbox one', 'ps4'],
                'out': ['hra na', 'ovládač', 'gamepad', 'puzdro', 'taška', 'nabíjačka', 'stojan']
            },
            'Hry na konzoly': {
                'in': ['hra na ps5', 'hra na ps4', 'hra na xbox', 'hra na nintendo', 'fifa', 'gta', 'call of duty', 'spider-man', 'god of war'],
                'out': ['konzola', 'ovládač']
            },

            # ---------------------------------------------------------------------
            # 💻 POČÍTAČE A KANCELÁRIA
            # ---------------------------------------------------------------------
            'Notebooky': { 
                'in': ['notebook', 'laptop', 'macbook', 'thinkpad', 'probook', 'vivobook', 'zenbook', 'aspire', 'inspiron', 'ideapad', 'surface'],
                'out': ['herný', 'gaming', 'rtx', 'taška', 'batoh', 'puzdro', 'klávesnica', 'myš', 'adaptér', 'displej', 'chladenie']
            },
            'Herné notebooky': {
                'in': ['herný notebook', 'gaming laptop', 'rtx 40', 'rtx 30', 'rog strix', 'tuf gaming', 'legion 5', 'legion 7', 'nitro 5', 'predator', 'msi katana'],
                'out': ['taška', 'batoh', 'puzdro', 'chladič']
            },
            'Grafické karty': {
                'in': ['grafická karta', 'geforce rtx', 'radeon rx', 'gtx 16', 'rtx 30', 'rtx 40', 'gpu', 'nvidia', 'amd radeon'],
                'out': ['notebook', 'pc zostava', 'počítač']
            },
            'Procesory': {
                'in': ['procesor', 'intel core', 'amd ryzen', 'cpu', 'intel pentium', 'intel celeron'],
                'out': ['notebook', 'počítač', 'pasta']
            },
            'Základné dosky': {
                'in': ['základná doska', 'motherboard', 'z790', 'b650', 'x670', 'lga1700', 'am5', 'am4'],
                'out': []
            },
            'Pevné disky': {
                'in': ['ssd disk', 'hdd disk', 'pevný disk', 'm.2 nvme', 'sata ssd', 'interný disk', 'externý disk', 'wd blue', 'samsung evo'],
                'out': []
            },
             'Monitory': {
                'in': ['monitor', 'lcd displej', 'herný monitor', '4k monitor', 'ips monitor', 'prehnutý monitor'],
                'out': ['notebook', 'držiak', 'kábel', 'stojan']
            },
            'Klávesnice': {
                'in': ['klávesnica', 'herná klávesnica', 'mechanická klávesnica', 'bezdrôtová klávesnica'],
                'out': ['notebook', 'náhradná']
            },
            'Myši': {
                'in': ['myš', 'herná myš', 'optická myš', 'bezdrôtová myš', 'vertikálna myš'],
                'out': ['podložka']
            },
            'Tlačiarne': {
                'in': ['tlačiareň', 'laserová tlačiareň', 'atramentová tlačiareň', 'multifunkčná tlačiareň', 'canon pixma', 'hp laserjet'],
                'out': ['toner', 'cartridge', 'náplň', 'papier']
            },

            # ---------------------------------------------------------------------
            # 🏠 DOMÁCE SPOTREBIČE
            # ---------------------------------------------------------------------
            'Automatické kávovary': {
                'in': ['automatický kávovar', 'espresso plnoautomat', 'delonghi magnifica', 'philips lattego', 'nivona', 'jura', 'krups'],
                'out': ['odvápňovač', 'čistič', 'káva', 'pohár', 'krmivo', 'brit', 'sausage']
            },
            'Pákové kávovary': {
                'in': ['pákový kávovar', 'espresso pákové', 'sage', 'delonghi dedica', 'gaggia'],
                'out': ['krmivo', 'brit', 'sausage', 'masáž']
            },
            'Kapsulové kávovary': {
                'in': ['kapsulový kávovar', 'kávovar na kapsule', 'dolce gusto', 'nespresso', 'tassimo'],
                'out': ['kapsule', 'stojan']
            },
            'Robotické vysávače': {
                'in': ['robotický vysávač', 'roomba', 'roborock', 'xiaomi robot vacuum', 'mopovací robot', 'eta master'],
                'out': ['kefka', 'filter', 'náhradná', 'batéria', 'vrecko', 'mop']
            },
            'Tyčové vysávače': {
                'in': ['tyčový vysávač', 'akumulátorový vysávač', 'dyson', 'rowenta air force', 'eta supurier', 'bosch unlimited'],
                'out': ['masáž']
            },
            'Vysávače': {
                'in': ['vreckový vysávač', 'bezvreckový vysávač', 'viacúčelový vysávač', 'priemyselný vysávač'],
                'out': ['robotický', 'tyčový', 'vrecká']
            },
            'Práčky s predným plnením': {
                'in': ['práčka s predným plnením', 'spredu plnená práčka', 'aeg', 'lg', 'samsung práčka'],
                'out': ['sušička', 'medzikus', 'prášok']
            },
            'Práčky s horným plnením': {
                'in': ['práčka s horným plnením', 'zhora plnená práčka', 'whirlpool', 'indesit'],
                'out': []
            },
            'Sušičky bielizne': {
                'in': ['sušička bielizne', 'sušička prádla', 'kondenzačná sušička', 'tepelné čerpadlo'],
                'out': ['práčka', 'držiak', 'vôňa']
            },
            'Americké chladničky': {
                'in': ['americká chladnička', 'side by side', 'dvojdverová chladnička', 'lg', 'samsung'],
                'out': []
            },
            'Chladničky': {
                'in': ['chladnička s mrazničkou', 'kombinovaná chladnička', 'vstavaná chladnička', 'monoklimatická'],
                'out': ['americká', 'autochladnička', 'taška']
            },
            'Umývačky riadu': {
                'in': ['umývačka riadu', 'vstavaná umývačka', 'stolná umývačka', 'bosch', 'beko'],
                'out': ['kapsule', 'soľ', 'leštidlo']
            },
            'Mikrovlnné rúry': {
                'in': ['mikrovlnná rúra', 'mikrovlnka', 'vstavaná mikrovlnka'],
                'out': ['poklop', 'taniere']
            },

            # ---------------------------------------------------------------------
            # 🌿 BÝVANIE A EXTERIÉR (ZÁHRADA)
            # ---------------------------------------------------------------------
            'Kosačky': {
                'in': ['benzínová kosačka', 'elektrická kosačka', 'aku kosačka', 'rotačná kosačka', 'strunová kosačka', 'krovinorez'],
                'out': ['olej', 'nôž', 'struna', 'robotická']
            },
            'Robotické kosačky': {
                'in': ['robotická kosačka', 'automower', 'landroid', 'gardena sileno'],
                'out': ['domček', 'garáž', 'kábel']
            },
            'Motorové píly': {
                'in': ['motorová píla', 'reťazová píla', 'benzínová píla', 'stihl', 'husqvarna', 'hecht', 'aku píla'],
                'out': ['reťaz', 'olej', 'pilník', 'lišta']
            },
            'Záhradný nábytok': {
                'in': ['záhradný nábytok', 'záhradný stôl', 'záhradná stolička', 'záhradné kreslo', 'záhradná lavica', 'lehátko', 'hojdačka', 'ratan'],
                'out': []
            },
             'Záhradné altánky': {
                'in': ['altánok', 'party stan', 'záhradný stan', 'pergola', 'prístrešok', 'slnečník'],
                'out': []
            },
            'Grily': {
                'in': ['záhradný gril', 'gril na drevené uhlie', 'plynový gril', 'weber', 'campingaz', 'elektrický gril'],
                'out': ['náradie', 'rošt', 'poťah', 'brikety', 'uhlie']
            },
            'Vysokotlakové čističe': {
                'in': ['vysokotlakový čistič', 'wapka', 'karcher k', 'nilfisk'],
                'out': ['hadica', 'nástavec', 'chémia']
            },
            'Bazény': {
                'in': ['bazén', 'nafukovací bazén', 'vírivka', 'intex', 'marimex'],
                'out': ['chémia', 'plachta', 'filter', 'sieťka']
            },

            # ---------------------------------------------------------------------
            # 🧸 SVET DETÍ
            # ---------------------------------------------------------------------
            'LEGO': {
                'in': ['lego stavebnica', 'lego city', 'lego technic', 'lego friends', 'lego star wars', 'lego duplo', 'lego harry potter', 'lego ninjago'],
                'out': ['box', 'krabica', 'tričko', 'hra']
            },
            'Kočíky': {
                'in': ['kombinovaný kočík', 'športový kočík', 'kočík pre bábiky', 'kočík 3v1', 'kinderkraft', 'cybex', 'buggy'],
                'out': ['pláštenka', 'taška', 'fusak', 'rukávnik', 'organizér']
            },
            'Autosedačky': {
                'in': ['autosedačka', 'vajíčko do auta', 'cybex', 'britax', 'maxi-cosi', 'podsedák'],
                'out': ['podložka', 'organizér', 'zrkadlo']
            },
            'Spoločenské hry': {
                'in': ['spoločenská hra', 'dosková hra', 'kartová hra', 'monopoly', 'activity', 'osadníci', 'párty hra', 'puzzle'],
                'out': []
            },
             'Hračky pre najmenších': {
                'in': ['hrkálka', 'hryzátko', 'chodítko', 'kolotoč nad postieľku', 'hracia deka', 'interaktívna hračka'],
                'out': []
            },

            # ---------------------------------------------------------------------
            # 💄 ZDRAVIE A VITALITA
            # ---------------------------------------------------------------------
            'Parfémy': {
                'in': ['parfém', 'toaletná voda', 'parfumovaná voda', 'hugo boss', 'calvin klein', 'versace', 'dior', 'chanel', 'armani'],
                'out': ['deodorant', 'sprchový gél', 'mlieko', 'voda po holení']
            },
            'Kozmetika': {
                'in': ['pleťový krém', 'maskara', 'make-up', 'rúž', 'šampón', 'kondicionér', 'sprchový gél', 'telové mlieko'],
                'out': []
            },
            'Proteíny': {
                'in': ['srvátkový proteín', 'whey protein', 'izolát', 'kazeín', 'vegan protein', 'gymbeam', 'biotechusa'],
                'out': ['tyčinka', 'shaker']
            },
            'Vitamíny a minerály': {
                'in': ['vitamín c', 'vitamín d', 'magnézium', 'zinok', 'omega 3', 'kolagén', 'multivitamín'],
                'out': []
            },

            # ---------------------------------------------------------------------
            # 🗑️ ODPADKOVÉ KOŠE A ZÁCHRANNÉ SIETE (DÔLEŽITÉ PRE ČISTOTU)
            # ---------------------------------------------------------------------
            'Krmivo pre psov': {
                'in': ['krmivo pre psov', 'granule pre psov', 'brit premium', 'sausage', 'dog', 'pre psov', 'mäsová konzerva'],
                'out': []
            },
            'Krmivo pre mačky': {
                'in': ['krmivo pre mačky', 'granule pre mačky', 'cat', 'pre mačky', 'whiskas'],
                'out': []
            },
            'Odborná literatúra': {
                'in': ['kniha', 'učebnica', 'zákon', 'právo', 'vzťahy', 'literatúra', 'publikácia'],
                'out': []
            },
            'Beletria': {
                'in': ['román', 'detektívka', 'poviedky', 'básne'],
                'out': []
            },
            'Fitness pomôcky': {
                'in': ['massage bar', 'masážna tyč', 'činka', 'expandér', 'roll', 'yoga', 'sklz'],
                'out': []
            }
        }
        
        # --- KROK 1: PRÍPRAVA DATABÁZY ---
        self.stdout.write("🗺️  Mapujem kategórie v systéme...")
        db_categories = Category.objects.all()
        target_map = {} 

        # Mapovanie pravidiel na reálne ID kategórií
        for rule_name in RULES.keys():
            # Skúsi nájsť presnú zhodu
            match = db_categories.filter(name__iexact=rule_name).first()
            # Ak nenájde, skúsi čiastočnú (fallback)
            if not match:
                match = db_categories.filter(name__icontains=rule_name).first()
            
            if match:
                target_map[rule_name] = match

        # --- KROK 2: APLIKÁCIA PRAVIDIEL (TRIEDENIE) ---
        self.stdout.write("⚙️ Spúšťam triediaci algoritmus...")
        
        products = Product.objects.all()
        total = products.count()
        processed = 0
        matched = 0
        
        batch = []
        BATCH_SIZE = 1000

        with transaction.atomic():
            for product in products:
                p_name = product.name.lower()
                best_category = None
                
                # Iterujeme cez pravidlá
                for rule_cat, logic in RULES.items():
                    if rule_cat not in target_map: continue
                    
                    # 1. OUT Check (Vylučovacia logika)
                    is_excluded = False
                    for bad_word in logic['out']:
                        if bad_word.lower() in p_name:
                            is_excluded = True
                            break
                    if is_excluded: continue
                    
                    # 2. IN Check (Inkluzívna logika)
                    for keyword in logic['in']:
                        if keyword.lower() in p_name:
                            best_category = target_map[rule_cat]
                            break
                    
                    if best_category: break # Našli sme zhodu, ideme na ďalší produkt

            # Ak sme našli lepšiu kategóriu, než má produkt teraz, zmeníme ju
            if best_category and product.category != best_category:
                product.category = best_category
                batch.append(product)
                matched += 1
            
            processed += 1
            if len(batch) >= BATCH_SIZE:
                Product.objects.bulk_update(batch, ['category'])
                batch = []
                self.stdout.write(f"   ...analyzovaných {processed}/{total} (Pretriedené: {matched})")

        if batch:
            Product.objects.bulk_update(batch, ['category'])
        
        self.stdout.write(self.style.SUCCESS(f"✅ TRIEDENIE HOTOVÉ. Zmenená kategória u {matched} produktov."))

        # =========================================================================
        # 🚀 KROK 3: SMART ACTIVATOR (Zapne len plné kategórie)
        # =========================================================================
        self.stdout.write("👁️  SMART ACTIVATOR: Analyzujem štruktúru webu...")
        
        # 1. Reset: Všetko skryjeme
        Category.objects.update(is_active=False)
        
        # 2. Nájdeme kategórie, ktoré majú produkty s aktívnymi ponukami
        # (Tým vyradíme kategórie, kde sú len "mŕtve" produkty bez ceny)
        active_cat_ids = Product.objects.filter(offers__active=True).values_list('category_id', flat=True).distinct()
        
        # Zapneme "Leaf" kategórie (tie čo majú produkty)
        Category.objects.filter(id__in=active_cat_ids).update(is_active=True)
        
        # 3. Rekurzívne zapneme rodičov (aby sa dalo preklikať v menu)
        self.stdout.write("🌲 Budujem navigačný strom...")
        
        # Cyklus beží, kým nachádza neaktívnych rodičov aktívnych detí
        changed = True
        while changed:
            # Nájdi rodičov, ktorí sú False, ale majú dieťa True
            inactive_parents = Category.objects.filter(
                is_active=False, 
                children__is_active=True
            ).distinct()
            
            if inactive_parents.exists():
                inactive_parents.update(is_active=True)
            else:
                changed = False

        visible_count = Category.objects.filter(is_active=True).count()
        self.stdout.write(self.style.SUCCESS(f"🎉 KOMPLET HOTOVO! Váš e-shop teraz zobrazuje {visible_count} relevantných kategórií."))