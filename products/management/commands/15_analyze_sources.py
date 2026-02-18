from django.core.management.base import BaseCommand
from products.models import Product
from django.db.models import Count

class Command(BaseCommand):
    help = 'Vypíše zoznam všetkých originálnych kategórií z feedov (pre stĺpec SRC)'

    def handle(self, *args, **kwargs):
        self.stdout.write("🕵️‍♂️  ANALÝZA ZDROJOVÝCH KATEGÓRIÍ...")
        self.stdout.write("---------------------------------------------------------")
        self.stdout.write(f"{'POČET':<10} | {'ORIGINÁLNY NÁZOV (Vlož do SRC)'}")
        self.stdout.write("---------------------------------------------------------")

        # Vytiahneme unikátne názvy kategórií a spočítame, koľko produktov v nich je
        # Zoradíme od najpočetnejších
        stats = Product.objects.values('original_category_text')\
            .annotate(total=Count('id'))\
            .order_by('-total')

        for item in stats:
            name = item['original_category_text']
            count = item['total']
            
            if name:
                self.stdout.write(f"{count:<10} | {name}")

        self.stdout.write("---------------------------------------------------------")
        self.stdout.write("✅ HOTOVO. Tieto názvy kopíruj do stĺpca SRC v Google Tabuľke.")