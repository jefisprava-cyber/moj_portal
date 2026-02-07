from django.core.management.base import BaseCommand
from products.models import Category
from django.utils.text import slugify
from django.db.models import Q

class Command(BaseCommand):
    help = 'Agresívne upratanie štruktúry podľa kľúčových slov'

    def handle(self, *args, **kwargs):
        self.stdout.write("🧹 Začínam HĹBKOVÉ upratovanie...")

        # 1. Definuj Hlavné Oddelenia (Tieto budú v menu)
        MAIN_CATS = {
            'Nábytok': ['nábytok', 'stolič', 'kresl', 'sedačk', 'stol', 'komod', 'regál', 'botník', 'matrac', 'posteľ', 'vak', 'nemý sluha', 'paraván', 'lavic', 'skrin', 'opierk', 'podnožk', 'čalúnenie'],
            'Zdravie': ['zdrav', 'lekár', 'liek', 'vitamín', 'biolamp', 'ortéz', 'bandáž', 'rehabilit', 'masáž', 'tlakomer', 'teplomer', 'inhalátor', 'orvos', 'egészség', 'gyógyászati'], # Aj maďarské
            'Elektronika': ['elektro', 'mobil', 'phone', 'tablet', 'počítač', 'notebook', 'tv', 'audio', 'video', 'foto', 'spotrebič', 'práčk', 'chladnič', 'vysávač', 'mixér', 'kávovar', 'usb', 'kábel'],
            'Dom a Záhrada': ['dom', 'záhrad', 'hobby', 'dielň', 'náradie', 'kober', 'záclon', 'záves', 'osvetlen', 'svietidl', 'žiarov', 'kvet', 'bazén', 'gril', 'háztartás', 'kuchyň', 'varenie', 'hrnce'],
            'Auto-Moto': ['auto', 'moto', 'pneu', 'disk', 'olej', 'kvapalin', 'stierač', 'autokober', 'kufor', 'nosič'],
            'Pre deti': ['deti', 'detsk', 'hračk', 'škol', 'bábät', 'kočík', 'autosedač', 'plienk'],
            'Šport a Voľný čas': ['šport', 'fitness', 'bicyk', 'stan', 'spacák', 'turist', 'futbal', 'hokej', 'lopt'],
            'Kancelária': ['kancelár', 'papier', 'tlačiar', 'zošit', 'perá', 'zakladač'],
            'Kozmetika a Drogéria': ['kozmetik', 'drogéri', 'parfém', 'vlas', 'pleť', 'zubn', 'mydl', 'sprch'],
            'Oblečenie a Móda': ['oblečeni', 'obuv', 'topánk', 'tričk', 'nohavic', 'bunda', 'čiapk'],
            'Knihy a Zábava': ['knih', 'film', 'hudb', 'hry', 'puzzle'],
        }

        # Vytvoríme hlavné kategórie a uložíme si ich objekty
        main_cat_objects = {}
        for name in MAIN_CATS.keys():
            slug = slugify(name)
            cat, _ = Category.objects.get_or_create(name=name, defaults={'slug': slug, 'parent': None})
            main_cat_objects[name] = cat
            # Uistíme sa, že sú na vrchu (nemajú rodiča)
            if cat.parent is not None:
                cat.parent = None
                cat.save()

        # Vytvoríme záchrannú sieť "Nezaradené"
        nezaradene, _ = Category.objects.get_or_create(name="Nezaradené", defaults={'slug': 'nezaradene-root', 'parent': None})
        if nezaradene.parent is not None:
            nezaradene.parent = None
            nezaradene.save()

        # 2. Prejdi VŠETKY kategórie, ktoré sú momentálne "Hore" (root), ale nie sú to naše Hlavné
        root_cats = Category.objects.filter(parent__isnull=True).exclude(id__in=[c.id for c in main_cat_objects.values()]).exclude(id=nezaradene.id)
        
        total = root_cats.count()
        self.stdout.write(f"Nájdených {total} kategórií na root úrovni, ktoré treba upratať.")

        moved = 0
        moved_to_nezaradene = 0

        for cat in root_cats:
            cat_name_lower = cat.name.lower()
            found_home = False

            # Hľadáme zhodu v kľúčových slovách
            for main_name, keywords in MAIN_CATS.items():
                for keyword in keywords:
                    if keyword in cat_name_lower:
                        # Našli sme zhodu! Presunieme pod hlavnú kategóriu
                        cat.parent = main_cat_objects[main_name]
                        cat.save()
                        # self.stdout.write(f"   -> '{cat.name}' presunuté do '{main_name}'")
                        found_home = True
                        moved += 1
                        break # Už sme našli, ideme na ďalšiu kategóriu
                if found_home:
                    break

            # Ak sme nenašli žiadnu zhodu, šupneme to do "Nezaradené"
            if not found_home:
                cat.parent = nezaradene
                cat.save()
                # self.stdout.write(f"   -> '{cat.name}' presunuté do 'Nezaradené'")
                moved_to_nezaradene += 1

        self.stdout.write(self.style.SUCCESS(f"✅ HOTOVO!"))
        self.stdout.write(f" - Zaradených do sekcií: {moved}")
        self.stdout.write(f" - Presunutých do 'Nezaradené': {moved_to_nezaradene}")
        self.stdout.write(f" - Teraz by si mal mať v menu len cca 12 hlavných položiek.")