from django.core.management.base import BaseCommand
from products.models import Category
from django.utils.text import slugify

class Command(BaseCommand):
    help = 'Presunie rozhádzané kategórie do hlavných oddelení'

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
                'Opierky chrbta na stoličku', 'Podnožky a opierky pod nohy', 'Podpera predlaktia'
            ],
            'Zdravie a Lekáreň': [
                'Zdravotnícke potreby', 'Zdravotní pomůcky', 'Zdravotné potreby', 
                'Zdravotní obuv a doplňky', 'Voľnopredajné lieky', 'Výživové doplnky a vitamíny',
                'Biolampy a světelná terapie', 'Biolámpák és fényterápia', 
                'Domácí lékařské přístroje', 'Otthoni orvosi eszközök',
                'Gyógyászati segédeszközök', 'Orvosok és szakrendelés részére',
                'Pro lékaře a ambulance', 'Wellness a fitness', 'Wellness és fitnesz',
                'Egészség a krása', 'Egészségügyi lábbelik és kiegészítők, tartozékok',
                'Potraviny a chudnutie'
            ],
            'Elektronika': [
                'Mobily, smart hodinky, tablety', 'Počítače a notebooky', 'TV, foto, audio-video',
                'Veľké spotrebiče', 'Domáce a osobné spotrebiče', 'Elektronika'
            ],
            'Dom, Záhrada a Hobby': [
                'Dom a záhrada', 'Drogéria a elektro', 'Kozmetika a hygiena', 
                'Akadálymentes háztartás', 'Bezbariérová domácnost', 
                'Potreby pre zvieratá', 'Šport', 'Šport a fitness'
            ],
            'Pre deti a Hračky': [
                'Deti a mamičky', 'Děti', 'Hračky, pre deti a bábätká', 
                'Školské potreby a pomôcky', 'Školský nábytok', 'Rastúce stoličky Fuxo'
            ],
            'Auto-Moto': [
                'Auto-moto', 'Autokoberce', 'Vane, koberce do kufru'
            ],
            'Kancelária a Firma': [
                'Kancelária', 'Doplnky pre kanceláriu', 'Kartotéky', 
                'Plechové šatňové skrine', 'Reklamné predmety'
            ],
            'Zábava, Knihy a Ostatné': [
                'Knihy', 'Knihy a poukazy', 'E-knihy', 'Filmy', 'Hudba', 
                'Darčeky', 'Ostatní', 'Egyéb', 'Nezaradené', 'Výpredaje, tipy', 'NOVINKY 2020',
                'Dlhodobo nedostupné produkty'
            ]
        }

        moved_count = 0

        for main_name, children_names in STRUCTURE.items():
            # 1. Vytvor alebo nájdi Hlavnú kategóriu
            main_slug = slugify(main_name)
            main_cat, created = Category.objects.get_or_create(
                name=main_name,
                defaults={'slug': main_slug, 'parent': None}
            )
            if created:
                self.stdout.write(f"➕ Vytvorená hlavná sekcia: {main_name}")

            # 2. Nájdi podkategórie a priraď im rodiča
            for child_name in children_names:
                # Hľadáme kategórie, ktoré majú tento názov a NEMAJÚ rodiča (sú teraz na vrchu)
                # Alebo majú rodiča, ale chceme ich presunúť (bezpečnejšie je brať len koreňové)
                cats_to_move = Category.objects.filter(name__iexact=child_name)
                
                for cat in cats_to_move:
                    # Kontrola, aby sme nepresúvali samotnú hlavnú kategóriu do seba
                    if cat.id == main_cat.id:
                        continue
                        
                    cat.parent = main_cat
                    cat.save()
                    moved_count += 1
                    # self.stdout.write(f"   -> Presunuté: {cat.name} pod {main_name}")

        self.stdout.write(self.style.SUCCESS(f"✅ HOTOVO! Presunutých {moved_count} kategórií do novej štruktúry."))