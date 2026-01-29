from django.shortcuts import render, redirect, get_object_or_404
from .models import Product, Category, Offer, PlannerItem, Bundle
from django.db.models import Min, Q
from django.contrib import messages

# --- KONFIGURÁCIA DOPRAVY ---
SHIPPING_STD = 3.90
SHIPPING_OVERSIZED = 19.90
FREE_SHIPPING_LIMIT = 300.00

# --- POMOCNÉ FUNKCIE ---
def get_session_key(request):
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key

def calculate_shipping(total_price, has_oversized):
    if total_price >= FREE_SHIPPING_LIMIT:
        return 0.0
    return SHIPPING_OVERSIZED if has_oversized else SHIPPING_STD

# --- 1. DOMOVSKÁ STRÁNKA ---
def home(request):
    products = Product.objects.all().order_by('?')[:8]
    bundles = Bundle.objects.all()
    
    if request.user.is_authenticated:
        cart_count = PlannerItem.objects.filter(user=request.user).count()
    else:
        cart_count = PlannerItem.objects.filter(session_key=get_session_key(request)).count()

    return render(request, 'products/home.html', {
        'products': products,
        'bundles': bundles,
        'cart_count': cart_count
    })

# --- 2. KATEGÓRIA (NOVÉ) ---
def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug)
    
    # Získame produkty v tejto kategórii ALEBO v jej podkategóriách
    products = Product.objects.filter(
        Q(category=category) | Q(category__parent=category)
    ).distinct()

    # Zoradenie (Sort)
    sort_by = request.GET.get('sort', 'default')
    if sort_by == 'price_asc':
        # Zoradenie podľa najnižšej ceny ponuky
        products = products.annotate(min_price=Min('offers__price')).order_by('min_price')
    elif sort_by == 'price_desc':
        products = products.annotate(min_price=Min('offers__price')).order_by('-min_price')
    elif sort_by == 'name':
        products = products.order_by('name')

    # Načítanie všetkých hlavných kategórií pre sidebar menu
    all_categories = Category.objects.filter(parent=None)

    return render(request, 'products/category_detail.html', {
        'category': category,
        'products': products,
        'all_categories': all_categories,
        'sort_by': sort_by
    })

# --- 3. VYHĽADÁVANIE ---
def search(request):
    query = request.GET.get('q')
    results = []
    
    if query:
        results = Product.objects.filter(
            Q(name__icontains=query) | 
            Q(description__icontains=query) |
            Q(ean__icontains=query) |
            Q(category__name__icontains=query)
        ).distinct()
    
    return render(request, 'products/search_results.html', {'products': results, 'query': query})

# --- 4. DETAILY PRODUKTOV ---
def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    offers = product.offers.filter(active=True).order_by('price')
    return render(request, 'products/product_detail.html', {'product': product, 'offers': offers})

def bundle_detail(request, bundle_slug):
    bundle = get_object_or_404(Bundle, slug=bundle_slug)
    products = bundle.products.all()
    return render(request, 'products/bundle_detail.html', {'bundle': bundle, 'products': products})

# --- 5. PLÁNOVAČ ---
def add_to_planner(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    criteria = {'product': product}
    if request.user.is_authenticated: criteria['user'] = request.user
    else: criteria['session_key'] = get_session_key(request)

    item, created = PlannerItem.objects.get_or_create(**criteria)
    if not created:
        item.quantity += 1
        item.save()
    
    messages.success(request, f"{product.name} pridaný do porovnávača.")
    return redirect('planner_view')

def add_bundle_to_planner(request, bundle_id):
    bundle = get_object_or_404(Bundle, id=bundle_id)
    sk = get_session_key(request)
    for product in bundle.products.all():
        criteria = {'product': product}
        if request.user.is_authenticated: criteria['user'] = request.user
        else: criteria['session_key'] = sk
        item, created = PlannerItem.objects.get_or_create(**criteria)
        if not created:
            item.quantity += 1
            item.save()
    messages.success(request, f"Zostava {bundle.name} bola pridaná do plánu.")
    return redirect('planner_view')

def remove_from_planner(request, item_id):
    item = get_object_or_404(PlannerItem, id=item_id)
    item.delete()
    return redirect('planner_view')

def planner_view(request):
    if request.user.is_authenticated: items = PlannerItem.objects.filter(user=request.user)
    else: items = PlannerItem.objects.filter(session_key=get_session_key(request))
    return render(request, 'products/planner.html', {'items': items})

# --- 6. SMART POROVNANIE ---
def comparison(request):
    if request.user.is_authenticated: items = PlannerItem.objects.filter(user=request.user)
    else: items = PlannerItem.objects.filter(session_key=get_session_key(request))

    if not items: return redirect('home')

    required_products = [item.product for item in items]
    
    mix_items_cost = 0
    mix_details = []
    shop_baskets = {} 

    for item in items:
        cheapest = item.product.offers.filter(active=True).order_by('price').first()
        if cheapest:
            cost = float(cheapest.price) * item.quantity
            mix_items_cost += cost
            mix_details.append({'product': item.product, 'offer': cheapest, 'quantity': item.quantity, 'cost': cost})
            
            s_name = cheapest.shop_name
            if s_name not in shop_baskets: shop_baskets[s_name] = {'total': 0.0, 'has_oversized': False}
            shop_baskets[s_name]['total'] += cost
            if item.product.is_oversized: shop_baskets[s_name]['has_oversized'] = True

    mix_shipping_cost = 0
    for shop_data in shop_baskets.values():
        mix_shipping_cost += calculate_shipping(shop_data['total'], shop_data['has_oversized'])

    mix_grand_total = mix_items_cost + mix_shipping_cost

    shop_names = Offer.objects.filter(product__in=required_products, active=True).values_list('shop_name', flat=True).distinct()
    single_shop_results = []

    for shop in shop_names:
        shop_items_cost = 0
        shop_has_oversized = False
        found_all = True
        
        for item in items:
            offer = item.product.offers.filter(shop_name=shop, active=True).first()
            if offer: 
                cost = float(offer.price) * item.quantity
                shop_items_cost += cost
                if item.product.is_oversized: shop_has_oversized = True
            else:
                found_all = False
                break
        
        if found_all:
            shipping = calculate_shipping(shop_items_cost, shop_has_oversized)
            total = shop_items_cost + shipping
            single_shop_results.append({
                'shop_name': shop,
                'items_price': shop_items_cost,
                'shipping_price': shipping,
                'total_price': total,
                'difference': total - mix_grand_total
            })

    single_shop_results.sort(key=lambda x: x['total_price'])
    if single_shop_results: single_shop_results[0]['is_winner'] = True

    return render(request, 'products/comparison.html', {
        'mix_items_cost': mix_items_cost,
        'mix_shipping_cost': mix_shipping_cost,
        'mix_grand_total': mix_grand_total,
        'mix_details': mix_details,
        'single_shop_results': single_shop_results,
        'free_shipping_limit': FREE_SHIPPING_LIMIT
    })