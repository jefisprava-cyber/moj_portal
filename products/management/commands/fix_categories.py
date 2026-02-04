from django.core.management.base import BaseCommand
from products.models import Product, Category
from django.utils.text import slugify

class Command(BaseCommand):
    help = 'Uprace kategórie presne podľa vzoru Alza'

    def handle(self, *args, **kwargs):
        self.stdout.write("🧹 Začínam upratovanie kategórií (Alza Style)...")

        # KĽÚČOVÉ SLOVÁ (Musia byť malé písmená bez dĺžňov ak sa dá, ale slugify to zvládne)
        RULES = {
            # 1. MOBILY A TABLETY (MobileOnline)
            'Mobily, smart hodinky, tablety': {
                'Smartfóny': ['iphone', 'samsung', 'xiaomi', 'motorola', 'realme', 'honor', 'smartfón', 'mobil'],
                'Smart hodinky': ['smartwatch', 'hodinky', 'garmin', 'apple watch', 'fitbit', 'amazfit'],
                'Tablety': ['ipad', 'tablet', 'lenovo tab', 'galaxy tab'],
                'Príslušenstvo': ['kryt', 'puzdro', 'nabíjačka', 'kábel', 'držiak', 'powerbanka'],
            },

            # 2. POČÍTAČE (MobileOnline + Elektro)
            'Počítače a notebooky': {
                'Notebooky': ['macbook', 'notebook', 'laptop', 'asus', 'hp', 'lenovo', 'dell', 'acer'],
                'Komponenty a príslušenstvo': ['klávesnica', 'myš', 'monitor', 'tlačiareň', 'router', 'usb', 'disk', 'ssd'],
                'Herné PC': ['herný počítač', 'geforce', 'rtx'],
            },

            # 3. TV A AUDIO (Elektro + MobileOnline)
            'TV, foto, audio-video': {
                'Televízory': ['televízor', 'tv', 'oled', 'qled', 'smart tv', '4k'],
                'Audio': ['slúchadlá', 'airpods', 'repro', 'jbl', 'sony', 'soundbar', 'rádio'],
                'Foto a Video': ['fotoaparát', 'kamera', 'gopro', 'instax', 'objektív'],
            },

            # 4. VEĽKÉ SPOTREBIČE (E-spotrebiče)
            'Veľké spotrebiče': {
                'Pranie a sušenie': ['práčka', 'sušička'],
                'Chladničky a mrazničky': ['chladnička', 'mraznička', 'americká chladnička', 'vinotéka'],
                'Varenie a pečenie': ['sporák', 'rúra', 'varná doska', 'digestor', 'odsávač', 'mikrovlnka'],
                'Umývačky riadu': ['umývačka riadu'],
            },

            # 5. MALÉ SPOTREBIČE (E-spotrebiče)
            'Domáce a osobné spotrebiče': {
                'Kuchynské potreby': ['kávovar', 'mixér', 'rýchlovarná kanvica', 'hriankovač', 'odšťavovač', 'gril'],
                'Starostlivosť o domácnosť': ['vysávač', 'žehlička', 'čistič', 'mop'],
                'Osobná starostlivosť': ['fén', 'kulma', 'holiaci strojček', 'zastrihávač', 'epilátor', 'zubná kefka'],
            },

            # 6. HRY A HRAČKY (Gorila + Dráčik/iné)
            'Hračky, pre deti a bábätká': {
                'Stavebnice a LEGO': ['lego', 'stavebnica', 'duplo'],
                'Pre bábätká': ['plienky', 'kočík', 'autosedačka', 'cumlík', 'fľaša', 'pampers'],
                'Hračky': ['bábika', 'autíčko', 'plyšák', 'hračka', 'puzzle', 'spoločenská hra'],
                'Školské potreby': ['školská taška', 'peračník', 'zošit'],
            },

            # 7. KNIHY (Gorila)
            'Knihy a poukazy': {
                'Beletria': ['román', 'kniha', 'beletria', 'detektívka', 'triler', 'poviedky', 'sága'],
                'Pre deti a mládež': ['rozprávky', 'leporelo', 'pre deti', 'harry potter', 'denník odvážneho'],
                'Odborná a náučná': ['učebnica', 'encyklopédia', 'kuchárka', 'slovník', 'mapa', 'sprievodca'],
                'Cudzojazyčná': ['english', 'german', 'anglický'],
            },

            # 8. DROGÉRIA A KOZMETIKA (MojaLekáreň + Notino)
            'Kozmetika, parfumy a krása': {
                'Parfumy': ['parfum', 'toaletná voda', 'voňavka', 'parfém'],
                'Pleťová a telová kozmetika': ['krém', 'sérum', 'maska', 'telové mlieko', 'mydlo', 'sprchový'],
                'Vlasová kozmetika': ['šampón', 'kondicionér', 'maska na vlasy', 'farba na vlasy'],
                'Líčenie': ['riasenka', 'rúž', 'make-up', 'púder'],
            },

            # 9. ZDRAVIE (MojaLekáreň)
            'Zdravie': {
                'Vitamíny a minerály': ['vitamín', 'minerál', 'kolagén', 'zinok', 'magnézium', 'vápnik', 'imunita'],
                'Voľnopredajné lieky': ['bolesť', 'horúčka', 'sirup', 'kvapky', 'sprej do nosa', 'náplasť', 'dezinfekcia'],
                'Zdravotnícke pomôcky': ['tlakomer', 'teplomer', 'inhalátor', 'bandáž'],
            }
        }

        # --- LOGIKA TRIEDENIA (Rovnaká ako predtým) ---
        category_map = {} 

        # 1. Vytvorenie štruktúry
        for main_cat_name, subcats in RULES.items():
            parent, _ = Category.objects.get_or_create(
                slug=slugify(main_cat_name),
                defaults={'name': main_cat_name, 'parent': None}
            )
            
            for sub_cat_name, keywords in subcats.items():
                child, _ = Category.objects.get_or_create(
                    slug=slugify(f"{main_cat_name}-{sub_cat_name}"),
                    defaults={'name': sub_cat_name, 'parent': parent}
                )
                for keyword in keywords:
                    category_map[keyword.lower()] = child

        # 2. Aplikácia na produkty
        products = Product.objects.all()
        updated = 0
        
        self.stdout.write(f"📦 Triedim {products.count()} produktov do Alza štruktúry...")

        for product in products:
            text_to_search = (product.name + " " + (product.description or "")).lower()
            
            matched_category = None
            
            # Hľadáme najlepšiu zhodu
            for keyword, category_obj in category_map.items():
                if keyword in text_to_search:
                    matched_category = category_obj
                    # Tu by sme mohli dať 'break', ale ak chceme byť presnejší, 
                    # môžeme nechať dobehnúť a brať poslednú (špecifickejšiu) zhodu.
                    # Pre rýchlosť dáme break.
                    break 
            
            if matched_category and product.category != matched_category:
                product.category = matched_category
                product.save()
                updated += 1
                if updated % 500 == 0:
                     self.stdout.write(f"   Pretriedené: {updated}...")

        self.stdout.write(self.style.SUCCESS(f"✅ Hotovo! {updated} produktov je teraz ako na Alze."))