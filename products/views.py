from django.shortcuts import render, redirect, get_object_or_404
from .models import Product, Category, Offer, PlannerItem, Bundle
from django.db.models import Min, Sum
from django.contrib import messages

# --- POMOCNÁ FUNKCIA NA ZÍSKANIE SESSION ---
def get_session_key(request):
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key

# --- DOMOVSKÁ STRÁNKA ---
def home(request):
    products = Product.objects.all().order_by('?')[:8] # Náhodných 8
    bundles = Bundle.objects.all() # Všetky balíčky (napr. Kuchyne)
    
    # Počítadlo v menu
    cart_count = 0
    if request.user.is_authenticated:
        cart_count = PlannerItem.objects.filter(user=request.user).count()
    else:
        cart_count = PlannerItem.objects.filter(session_key=get_session_key(request)).count()

    return render(request, 'products/home.html', {
        'products': products,
        'bundles': bundles,
        'cart_count': cart_count
    })

# --- PRIDAŤ DO PLÁNOVAČA ---
def add_to_planner(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    # Určíme, komu to patrí (User alebo Session)
    criteria = {'product': product}
    if request.user.is_authenticated:
        criteria['user'] = request.user
    else:
        criteria['session_key'] = get_session_key(request)

    # Vytvoríme alebo zvýšime počet
    item, created = PlannerItem.objects.get_or_create(**criteria)
    if not created:
        item.quantity += 1
        item.save()
    
    messages.success(request, f"{product.name} pridaný do porovnávača.")
    return redirect('planner_view')

# --- ZOBRAZIŤ PLÁNOVAČ (Košík) ---
def planner_view(request):
    if request.user.is_authenticated:
        items = PlannerItem.objects.filter(user=request.user)
    else:
        items = PlannerItem.objects.filter(session_key=get_session_key(request))

    return render(request, 'products/planner.html', {'items': items})

# --- ODSTRÁNIŤ Z PLÁNOVAČA ---
def remove_from_planner(request, item_id):
    item = get_object_or_404(PlannerItem, id=item_id)
    # Bezpečnostná kontrola (aby si nezmazal cudzí item)
    if (request.user.is_authenticated and item.user == request.user) or \
       (not request.user.is_authenticated and item.session_key == request.session.session_key):
        item.delete()
    
    return redirect('planner_view')

# --- 🧠 MOZOG: POROVNANIE CIEN ---
def comparison(request):
    # 1. Načítame položky z plánovača
    if request.user.is_authenticated:
        items = PlannerItem.objects.filter(user=request.user)
    else:
        items = PlannerItem.objects.filter(session_key=get_session_key(request))

    if not items:
        return redirect('home')

    required_products = [item.product for item in items]
    
    # 2. Stratégia: MIX OBCHODOV (Najnižšia cena pre každý produkt zvlášť)
    mix_total = 0
    mix_details = []
    
    for item in items:
        # Nájdi najlacnejšiu ponuku pre tento produkt
        cheapest_offer = item.product.offers.filter(active=True).order_by('price').first()
        
        if cheapest_offer:
            cost = cheapest_offer.price * item.quantity
            mix_total += cost
            mix_details.append({
                'product': item.product,
                'offer': cheapest_offer,
                'quantity': item.quantity,
                'cost': cost
            })
        else:
            # Ak produkt nikde nemajú (Edge case)
            pass

    # 3. Stratégia: JEDEN OBCHOD (Všetko naraz)
    # Získame zoznam všetkých obchodov, ktoré majú aspoň niečo z nášho zoznamu
    shop_names = Offer.objects.filter(product__in=required_products, active=True).values_list('shop_name', flat=True).distinct()
    
    single_shop_results = []

    for shop in shop_names:
        shop_total = 0
        found_all = True
        shop_items = []
        
        for item in items:
            offer = item.product.offers.filter(shop_name=shop, active=True).first()
            if offer:
                cost = offer.price * item.quantity
                shop_total += cost
                shop_items.append({'product': item.product, 'offer': offer})
            else:
                found_all = False
                break # Tento obchod nemá všetko, preskakujeme
        
        if found_all:
            diff = shop_total - mix_total
            single_shop_results.append({
                'shop_name': shop,
                'total_price': shop_total,
                'difference': diff, # O koľko je to drahšie ako Mix
                'is_winner': False # Neskôr určíme víťaza
            })

    # Zoradíme obchody od najlacnejšieho
    single_shop_results.sort(key=lambda x: x['total_price'])
    
    # Označíme najlepší "Jeden obchod"
    if single_shop_results:
        single_shop_results[0]['is_winner'] = True

    return render(request, 'products/comparison.html', {
        'mix_total': mix_total,
        'mix_details': mix_details,
        'single_shop_results': single_shop_results,
    })