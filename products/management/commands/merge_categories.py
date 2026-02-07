from django.core.management.base import BaseCommand
from products.models import Category
from django.db.models import Count

class Command(BaseCommand):
    help = 'Zlúči duplicitné kategórie (rovnaký názov a rodič) do jednej.'

    def handle(self, *args, **kwargs):
        self.stdout.write("🔍 Hľadám duplicitné kategórie...")

        # 1. Nájdi skupiny kategórií, ktoré majú rovnaký názov a rodiča
        duplicates = Category.objects.values('name', 'parent').annotate(count=Count('id')).filter(count__gt=1)

        total_groups = duplicates.count()
        self.stdout.write(f"Našiel som {total_groups} skupín duplicít. Začínam zlučovanie...")

        merged_count = 0

        for dup in duplicates:
            name = dup['name']
            parent_id = dup['parent']
            
            # Nájdi všetky kategórie v tejto skupine
            cats = list(Category.objects.filter(name=name, parent_id=parent_id))
            
            # Zoradíme ich tak, aby sme zachovali tú s "najkrajším" slugom (najkratším)
            # Napr. chceme zachovať 'elektronika' a zmazať 'elektronika-a1b2...'
            cats.sort(key=lambda x: len(x.slug))
            
            target_cat = cats[0] # Táto ostane (Master)
            cats_to_merge = cats[1:] # Tieto zlúčime a zmažeme
            
            self.stdout.write(f"  Doing: '{name}' -> Ponechávam ID {target_cat.id} ({target_cat.slug})")

            for c in cats_to_merge:
                # 1. Presuň produkty
                products_count = c.products.count()
                if products_count > 0:
                    c.products.update(category=target_cat)
                
                # 2. Presuň podkategórie (deti)
                children_count = c.children.count()
                if children_count > 0:
                    c.children.update(parent=target_cat)
                
                # 3. Zmaž duplicitnú kategóriu
                c.delete()
                merged_count += 1

        self.stdout.write(self.style.SUCCESS(f'✅ HOTOVO! Zlúčených a zmazaných {merged_count} nadbytočných kategórií.'))