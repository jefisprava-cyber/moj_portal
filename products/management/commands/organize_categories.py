from django.core.management.base import BaseCommand
from products.models import Category
from django.utils.text import slugify

class Command(BaseCommand):
    help = 'Presunie rozhádzané kategórie do hlavných oddelení (odolné voči duplicitám)'

    def handle(self, *args, **kwargs):
        self.stdout.write("🏗️ Začínam reorganizáciu stromu kategórií...")

        # Definícia štruktúry: HLAVNÁ KATEGÓRIA -> [Zoznam kategórií, ktoré tam presunieme]
        STRUCTURE = {
            'Nábytok a Bývanie': [
                'Stoličky', 'Stoly a stolíky', 'Kreslá', 'Sedačky', 'Komody', 'Regály', 
                'Botníky', 'Matrace', 'Postele', 'Sedacie vaky a vrecia', 'Nemý sluha',
                'Kancelársky nábytok', 'Detský nábytok', 'Záhradný nábytok', 'Paravány',
                'Kovová kostra, čalúnenie', 'Šatňové lavice', 'Plechové skrine', 
                'Stolíky pod notebook', 'Vankúšiky', 'Náhradné diely na stoličky',
                'Opierky chrbta na stoličku', 'Podnožky a opierky pod nohy', 'Podpera predlaktia',
                'Záclony', 'Závesy', 'Koberce', 'Osvetlenie', 'Svietidlá'
            ],
            'Zdravie a Lekáreň': [
                'Zdravotnícke potreby', 'Zdravotní pomůcky', 'Zdravotné potreby', 
                'Zdravotní obuv a doplňky', 'Voľnopredajné lieky', 'Výživové doplnky a vitamíny',
                'Biolampy a světelná terapie', 'Biolámpák és fényterápia', 
                'Domácí lékařské přístroje', 'Otthoni orvosi eszközök',
                'Gyógyászati segédeszközök', 'Orvosok és szakrendelés részére',
                'Pro lékaře a ambulance', 'Wellness a fitness', 'Wellness és fitnesz',
                'Egészség a krása', 'Egészségügyi lábbelik és kiegészítők, tartozékok',
                'Potraviny a chudnutie', 'Zdravie', 'Zdravie a krása', 'Zdraví a krása'
            ],
            'Elektronika': [
                'Mobily, smart hodinky, tablety', 'Počítače a notebooky', 'TV, foto, audio-video',
                'Veľké spotrebiče', 'Domáce a osobné spotrebiče', 'Elektronika'
            ],
            'Dom, Záhrada a Hobby': [
                'Dom a záhrada', 'Drogéria a elektro', 'Kozmetika a hygiena', 
                'Akadálymentes háztartás', 'Bezbariérová domácnost', 
                'Potreby pre zvieratá', 'Šport', 'Šport a fitness', 'Auto-moto',
                'Autokoberce', 'Vane, koberce do kufru'
            ],
            'Pre deti a Hračky': [
                'Deti a mamičky', 'Děti', 'Hračky, pre deti a bábätká', 
                'Školské potreby a pomôcky', 'Školský nábytok', 'Rastúce stoličky Fuxo'
            ],
            'Kancelária a Firma': [
                'Kancelária', 'Doplnky pre kanceláriu', 'Kartotéky', 
                'Plechové šatňové skrine', 'Reklamné predmety'
            ],
            'Zábava, Knihy a Ostatné': [
                'Knihy', 'Knihy a poukazy', 'E-knihy', 'Filmy', 'Hudba', 
                'Darčeky', 'Ostatní', 'Egyéb', 'Nezaradené', 'Výpredaje, tipy', 'NOVINKY 2020',
                'Dlhodobo nedostupné produkty', 'TOP Produkty'
            ]
        }

        moved_count = 0

        for main_name, children_names in STRUCTURE.items():
            # --- BEZPEČNÉ VYTVORENIE HLAVNEJ KATEGÓRIE ---
            # Nájde všetky kategórie s týmto názvom
            existing_cats = Category.objects.filter(name__iexact=main_name)
            
            if existing_cats.exists():
                # Ak už existujú, zoberieme prvú ako Hlavnú
                main_cat = existing_cats.first()
                # Ak ich je viac, tie ostatné zlúčime do tej prvej
                if existing_cats.count() > 1:
                    self.stdout.write(f"⚠️ Nájdená duplicita pre '{main_name}', zlučujem...")
                    for dup in existing_cats[1:]:
                        dup.products.update(category=main_cat)
                        dup.children.update(parent=main_cat)
                        dup.delete()
            else:
                # Ak neexistuje, vytvoríme novú
                main_slug = slugify(main_name)
                # Ošetrenie unikátnosti slugu
                if Category.objects.filter(slug=main_slug).exists():
                    main_slug = f"{main_slug}-root"
                
                main_cat = Category.objects.create(name=main_name, slug=main_slug, parent=None)
                self.stdout.write(f"➕ Vytvorená hlavná sekcia: {main_name}")

            # --- PRESUN PODKATEGÓRIÍ ---
            for child_name in children_names:
                # Hľadáme kategórie, ktoré majú tento názov
                cats_to_move = Category.objects.filter(name__iexact=child_name)
                
                for cat in cats_to_move:
                    # Aby sme nepresunuli hlavnú kategóriu samu do seba
                    if cat.id == main_cat.id:
                        continue
                        
                    cat.parent = main_cat
                    cat.save()
                    moved_count += 1

        self.stdout.write(self.style.SUCCESS(f"✅ HOTOVO! Presunutých {moved_count} kategórií do novej štruktúry."))