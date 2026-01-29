from django.shortcuts import render, redirect, get_object_or_404
from .models import Product, Category, Offer, PlannerItem, Bundle
from django.db.models import Min, Q
from django.contrib import messages

# Pomocná funkcia pre session
def get_session_key(request):
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key

# --- DOMOV ---
def home(request):
    products = Product.objects.all().order_by('?')[:8]
    bundles = Bundle.objects.all()
    if request.user.is_authenticated:
        cart_count = PlannerItem.objects.filter(user=request.user).count()
    else:
        cart_count = PlannerItem.objects.filter(session_key=get_session_key(request)).count()

    return render(request, 'products/home.html', {'products': products, 'bundles': bundles, 'cart_count': cart_count})

# --- VYHĽADÁVANIE (NOVÉ) ---
def search(request):
    query = request.GET.get('q')
    results = []
    
    if query:
        # Hľadáme v názve, popise ALEBO v EAN kóde
        results = Product.objects.filter(
            Q(name__icontains=query) | 
            Q(description__icontains=query) |
            Q(ean__icontains=query) |
            Q(category__name__icontains=query)
        ).distinct()
    
    return render(request, 'products/search_results.html', {'products': results, 'query': query})

# --- OSTATNÉ FUNKCIE (Bez zmeny) ---
def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    offers = product.offers.filter(active=True).order_by('price')
    return render(request, 'products/product_detail.html', {'product': product, 'offers': offers})

def bundle_detail(request, bundle_slug):
    bundle = get_object_or_404(Bundle, slug=bundle_slug)
    products = bundle.products.all()
    return render(request, 'products/bundle_detail.html', {'bundle': bundle, 'products': products})

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
    messages.success(request, f"Zostava {bundle.name} pridaná do plánu.")
    return redirect('planner_view')

def planner_view(request):
    if request.user.is_authenticated: items = PlannerItem.objects.filter(user=request.user)
    else: items = PlannerItem.objects.filter(session_key=get_session_key(request))
    return render(request, 'products/planner.html', {'items': items})

def remove_from_planner(request, item_id):
    item = get_object_or_404(PlannerItem, id=item_id)
    item.delete()
    return redirect('planner_view')

def comparison(request):
    if request.user.is_authenticated: items = PlannerItem.objects.filter(user=request.user)
    else: items = PlannerItem.objects.filter(session_key=get_session_key(request))
    if not items: return redirect('home')

    required_products = [item.product for item in items]
    mix_total = 0
    mix_details = []
    
    for item in items:
        cheapest = item.product.offers.filter(active=True).order_by('price').first()
        if cheapest:
            cost = cheapest.price * item.quantity
            mix_total += cost
            mix_details.append({'product': item.product, 'offer': cheapest, 'quantity': item.quantity, 'cost': cost})

    shop_names = Offer.objects.filter(product__in=required_products, active=True).values_list('shop_name', flat=True).distinct()
    single_shop_results = []
    for shop in shop_names:
        shop_total = 0
        found_all = True
        for item in items:
            offer = item.product.offers.filter(shop_name=shop, active=True).first()
            if offer: shop_total += offer.price * item.quantity
            else:
                found_all = False
                break
        if found_all:
            single_shop_results.append({'shop_name': shop, 'total_price': shop_total, 'difference': shop_total - mix_total})
    single_shop_results.sort(key=lambda x: x['total_price'])
    
    return render(request, 'products/comparison.html', {'mix_total': mix_total, 'mix_details': mix_details, 'single_shop_results': single_shop_results})