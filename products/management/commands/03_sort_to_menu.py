from django.core.management.base import BaseCommand
from products.models import Category
from django.utils.text import slugify

class Command(BaseCommand):
    help = 'Agresívne upratanie štruktúry podľa kľúčových slov'

    def handle(self, *args, **kwargs):
        self.stdout.write("🧹 Začínam HĹBKOVÉ upratovanie...")

        MAIN_CATS = {
            'Nábytok': ['nábytok', 'stolič', 'kresl', 'sedačk', 'stol', 'komod', 'regál', 'botník', 'matrac', 'posteľ', 'vak', 'nemý sluha', 'paraván', 'lavic', 'skrin', 'opierk', 'podnožk', 'čalúnenie', 'sedák'],
            'Zdravie': ['zdrav', 'lekár', 'liek', 'vitamín', 'biolamp', 'ortéz', 'bandáž', 'rehabilit', 'masáž', 'tlakomer', 'teplomer', 'inhalátor', 'orvos', 'egészség', 'gyógyászati', 'wellness'],
            'Elektronika': ['elektro', 'mobil', 'phone', 'tablet', 'počítač', 'notebook', 'tv', 'audio', 'video', 'foto', 'spotrebič', 'práčk', 'chladnič', 'vysávač', 'mixér', 'kávovar', 'usb', 'kábel'],
            'Dom a Záhrada': ['dom', 'záhrad', 'hobby', 'dielň', 'náradie', 'kober', 'záclon', 'záves', 'osvetlen', 'svietidl', 'žiarov', 'kvet', 'bazén', 'gril', 'háztartás', 'kuchyň', 'varenie', 'hrnce', 'riad', 'vane', 'kúpeľň'],
            'Auto-Moto': ['auto', 'moto', 'pneu', 'disk', 'olej', 'kvapalin', 'stierač', 'autokober', 'kufor', 'nosič'],
            'Pre deti': ['deti', 'detsk', 'hračk', 'škol', 'bábät', 'kočík', 'autosedač', 'plienk'],
            'Šport a Voľný čas': ['šport', 'fitness', 'bicyk', 'stan', 'spacák', 'turist', 'futbal', 'hokej', 'lopt'],
            'Kancelária': ['kancelár', 'papier', 'tlačiar', 'zošit', 'perá', 'zakladač', 'kartoték'],
            'Kozmetika a Drogéria': ['kozmetik', 'drogéri', 'parfém', 'vlas', 'pleť', 'zubn', 'mydl', 'sprch'],
            'Oblečenie a Móda': ['oblečeni', 'obuv', 'topánk', 'tričk', 'nohavic', 'bunda', 'čiapk'],
            'Knihy a Zábava': ['knih', 'film', 'hudb', 'hry', 'puzzle', 'darček'],
        }

        # 1. Získanie alebo vytvorenie hlavných kategórií (Bezpečne!)
        main_cat_objects = {}
        
        for name in MAIN_CATS.keys():
            slug = slugify(name)
            
            # Skús nájsť podľa názvu
            cat = Category.objects.filter(name__iexact=name).first()
            
            if not cat:
                # Skús nájsť podľa slugu
                cat = Category.objects.filter(slug=slug).first()
            
            if not cat:
                # Ak neexistuje, vytvor novú
                cat = Category.objects.create(name=name, slug=slug, parent=None)
            else:
                # Ak existuje, uisti sa, že je na vrchu a má správny názov
                cat.parent = None
                cat.name = name # Zjednotíme názov (napr. "Dom a záhrada" -> "Dom a Záhrada")
                cat.save()

            main_cat_objects[name] = cat

        # Záchranná sieť "Nezaradené"
        nezaradene = Category.objects.filter(slug='nezaradene').first()
        if not nezaradene:
            nezaradene = Category.objects.create(name="Nezaradené", slug='nezaradene', parent=None)
        
        nezaradene.parent = None
        nezaradene.save()

        # 2. Upratovanie ROOT kategórií
        # Vyberieme všetky root kategórie okrem našich hlavných
        root_cats = Category.objects.filter(parent__isnull=True).exclude(id__in=[c.id for c in main_cat_objects.values()]).exclude(id=nezaradene.id)
        
        total = root_cats.count()
        self.stdout.write(f"Nájdených {total} kategórií na root úrovni, ktoré treba upratať.")

        moved = 0
        moved_to_nezaradene = 0

        for cat in root_cats:
            cat_name_lower = cat.name.lower()
            found_home = False

            # Hľadáme zhodu
            for main_name, keywords in MAIN_CATS.items():
                for keyword in keywords:
                    if keyword in cat_name_lower:
                        cat.parent = main_cat_objects[main_name]
                        cat.save()
                        found_home = True
                        moved += 1
                        break 
                if found_home:
                    break

            # Ak sme nenašli zhodu, šup do Nezaradené
            if not found_home:
                cat.parent = nezaradene
                cat.save()
                moved_to_nezaradene += 1

        self.stdout.write(self.style.SUCCESS(f"✅ HOTOVO!"))
        self.stdout.write(f" - Zaradených do sekcií: {moved}")
        self.stdout.write(f" - Presunutých do 'Nezaradené': {moved_to_nezaradene}")