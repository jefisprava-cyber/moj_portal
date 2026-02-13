from django.shortcuts import render, redirect, get_object_or_404
from .models import Product, Category, Offer, PlannerItem, Bundle, SavedPlan, SavedPlanItem, Review
from .forms import ReviewForm
from django.db.models import Min, Q, Sum, Max
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.core.management import call_command
import json 
import sys
from io import StringIO

# --- KONFIGURÁCIA DOPRAVY ---
SHIPPING_STD = 3.90
SHIPPING_OVERSIZED = 19.90
FREE_SHIPPING_LIMIT = 300.00

# --- POMOCNÉ FUNKCIE ---
def get_session_key(request):
    """Vráti session key pre neprihláseného užívateľa."""
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key

def calculate_shipping(total_price, has_oversized):
    """Vypočíta cenu dopravy podľa sumy a veľkosti tovaru."""
    if total_price >= FREE_SHIPPING_LIMIT:
        return 0.0
    return SHIPPING_OVERSIZED if has_oversized else SHIPPING_STD

def get_all_children(category):
    """Bezpečná verzia na získanie všetkých podkategórií (rieši 'canceled' status)."""
    descendants = []
    stack = [category]
    visited = {category.id}
    limit = 0
    while stack and limit < 1000:
        limit += 1
        current = stack.pop()
        for child in current.children.all():
            if child.id not in visited:
                visited.add(child.id)
                descendants.append(child)
                stack.append(child)
    return descendants

# ==========================================
# 1. HLAVNÉ STRÁNKY
# ==========================================

def home(request):
    """Domovská stránka s produktami, balíčkami a kategóriami."""
    # OPRAVA: Len aktívne kategórie
    all_categories = Category.objects.filter(parent=None, is_active=True)
    
    # Načítame produkty aj s ich kategóriami pre rýchlosť
    products = Product.objects.select_related('category').filter(category__is_active=True).order_by('-created_at')[:8]
    bundles = Bundle.objects.all()
    
    if request.user.is_authenticated:
        cart_count = PlannerItem.objects.filter(user=request.user).count()
    else:
        cart_count = PlannerItem.objects.filter(session_key=get_session_key(request)).count()

    return render(request, 'products/home.html', {
        'products': products,
        'bundles': bundles,
        'cart_count': cart_count,
        'all_categories': all_categories
    })

def category_detail(request, slug):
    """Zobrazenie kategórie a jej produktov s filtrovaním."""
    # OPRAVA: Kontrola is_active=True
    category = get_object_or_404(Category, slug=slug, is_active=True)
    
    # 1. Získame ID všetkých podkategórií hlboko v strome
    all_cats = [category] + get_all_children(category)
    cat_ids = [c.id for c in all_cats]
    
    # 2. INTELIGENTNÁ OPRAVA (Smart Fix pre prázdne kategórie):
    # Hľadáme produkty podľa ID ALEBO podľa názvu kategórie
    products = Product.objects.filter(
        Q(category_id__in=cat_ids) | 
        Q(category__name__icontains=category.name)
    ).select_related('category').distinct()

    sort_by = request.GET.get('sort', 'default')
    
    # --- LOGIKA TRIEDENIA ---
    if sort_by == 'price_asc':
        products = products.order_by('price')
    elif sort_by == 'price_desc':
        products = products.order_by('-price')
    elif sort_by == 'name':
        products = products.order_by('name')
    else:
        products = products.order_by('-created_at')
    
    # OPRAVA: Len aktívne kategórie
    all_categories = Category.objects.filter(parent=None, is_active=True)

    return render(request, 'products/category_detail.html', {
        'category': category,
        'products': products,
        'all_categories': all_categories,
        'sort_by': sort_by
    })

def search(request):
    """Vyhľadávanie produktov."""
    query = request.GET.get('q')
    results = Product.objects.none()
    
    if query:
        results = Product.objects.filter(
            Q(name__icontains=query) | 
            Q(description__icontains=query) |
            Q(ean__icontains=query) |
            # OPRAVA: Len v aktívnych kategóriách
            Q(category__name__icontains=query, category__is_active=True)
        ).select_related('category').filter(category__is_active=True).distinct()
    
    # OPRAVA: Len aktívne kategórie
    all_categories = Category.objects.filter(parent=None, is_active=True)

    return render(request, 'products/product_list.html', {
        'products': results, 
        'search_query': query,
        'all_categories': all_categories,
        'is_search': True 
    })

def privacy_policy(request):
    return render(request, 'pages/gdpr.html')

# ==========================================
# 2. DETAIL PRODUKTU (S RECENZIAMI)
# ==========================================

def product_detail(request, slug): 
    product = get_object_or_404(Product, slug=slug)
    offers = product.offers.filter(active=True).order_by('-is_sponsored', 'price')
    
    form = ReviewForm()
    if request.method == 'POST' and request.user.is_authenticated:
        form = ReviewForm(request.POST)
        if form.is_valid():
            existing = Review.objects.filter(product=product, user=request.user).exists()
            if existing:
                messages.warning(request, "Tento produkt ste už hodnotili.")
            else:
                review = form.save(commit=False)
                review.product = product
                review.user = request.user
                review.save()
                messages.success(request, "Ďakujeme za vaše hodnotenie!")
            return redirect('product_detail', slug=slug)

    history = product.price_history.all().order_by('date')
    dates = [h.date.strftime("%d.%m.") for h in history]
    min_prices = [float(h.min_price) for h in history]
    avg_prices = [float(h.avg_price) for h in history]
    
    return render(request, 'products/product_detail.html', {
        'product': product, 
        'offers': offers,
        'form': form,
        'reviews': product.reviews.all().order_by('-created_at'),
        'chart_dates': json.dumps(dates),
        'chart_min_prices': json.dumps(min_prices),
        'chart_avg_prices': json.dumps(avg_prices)
    })

def bundle_detail(request, bundle_slug):
    bundle = get_object_or_404(Bundle, slug=bundle_slug)
    products = bundle.products.all()
    total_price = 0
    for p in products:
        if p.price > 0:
            total_price += p.price
        else:
            offer = p.offers.order_by('price').first()
            if offer:
                total_price += offer.price

    return render(request, 'products/bundle_detail.html', {
        'bundle': bundle, 
        'products': products,
        'total_price': total_price
    })

# ==========================================
# 3. NÁKUPNÝ PLÁNOVAČ (KOŠÍK)
# ==========================================

def add_to_planner(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    criteria = {'product': product}
    
    if request.user.is_authenticated:
        criteria['user'] = request.user
    else:
        criteria['session_key'] = get_session_key(request)

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
        if request.user.is_authenticated:
            criteria['user'] = request.user
        else:
            criteria['session_key'] = sk
            
        item, created = PlannerItem.objects.get_or_create(**criteria)
        if not created:
            item.quantity += 1
            item.save()
            
    messages.success(request, f"Zostava {bundle.name} bola pridaná do plánu.")
    return redirect('planner_view')

def remove_from_planner(request, item_id):
    if request.user.is_authenticated:
        item = get_object_or_404(PlannerItem, id=item_id, user=request.user)
    else:
        item = get_object_or_404(PlannerItem, id=item_id, session_key=request.session.session_key)

    item.delete()
    messages.info(request, "Položka bola odstránená.")
    return redirect('planner_view')

def planner_view(request):
    # 👇👇👇 OPRAVENÁ VERZIA: PRIRADENIE NAJLACNEJŠEJ PONUKY 👇👇👇
    if request.user.is_authenticated:
        items = PlannerItem.objects.filter(user=request.user).select_related('product')
    else:
        items = PlannerItem.objects.filter(session_key=get_session_key(request)).select_related('product')
    
    total_estimated = 0
    for item in items:
        # 1. Vždy nájdi najlacnejšiu ponuku (aj keď produkt má cenu)
        cheapest = item.product.offers.filter(active=True).order_by('price').first()
        
        # 2. Ulož ju do objektu pre šablónu (HTML)
        item.cheapest_offer = cheapest

        # 3. Výpočet ceny pre súčet
        price = item.product.price
        if price == 0 and cheapest:
            price = cheapest.price
        
        total_estimated += price * item.quantity

    return render(request, 'products/planner.html', {'items': items, 'total_price': total_estimated})

# ==========================================
# 4. SMART POROVNANIE
# ==========================================

def comparison(request):
    if request.user.is_authenticated:
        items = PlannerItem.objects.filter(user=request.user).select_related('product')
    else:
        items = PlannerItem.objects.filter(session_key=get_session_key(request)).select_related('product')

    if not items:
        return redirect('home')

    required_products = [item.product for item in items]
    
    # A. MIX STRATÉGIA
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
            if s_name not in shop_baskets:
                shop_baskets[s_name] = {'total': 0.0, 'has_oversized': False}
            
            shop_baskets[s_name]['total'] += cost
            if getattr(item.product, 'is_oversized', False):
                shop_baskets[s_name]['has_oversized'] = True

    mix_shipping_cost = 0
    for shop_data in shop_baskets.values():
        mix_shipping_cost += calculate_shipping(shop_data['total'], shop_data['has_oversized'])

    mix_grand_total = mix_items_cost + mix_shipping_cost

    # B. JEDEN OBCHOD STRATÉGIA
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
                if getattr(item.product, 'is_oversized', False):
                    shop_has_oversized = True
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
    if single_shop_results:
        single_shop_results[0]['is_winner'] = True

    return render(request, 'products/comparison.html', {
        'mix_items_cost': mix_items_cost,
        'mix_shipping_cost': mix_shipping_cost,
        'mix_grand_total': mix_grand_total,
        'mix_details': mix_details,
        'single_shop_results': single_shop_results,
        'free_shipping_limit': FREE_SHIPPING_LIMIT
    })

# ==========================================
# 5. UŽÍVATEĽSKÉ KONTO A UKLADANIE
# ==========================================

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            session_key = get_session_key(request)
            anon_items = PlannerItem.objects.filter(session_key=session_key)
            for item in anon_items:
                existing_item = PlannerItem.objects.filter(user=user, product=item.product).first()
                if existing_item:
                    existing_item.quantity += item.quantity
                    existing_item.save()
                    item.delete()
                else:
                    item.user = user
                    item.session_key = None
                    item.save()
            messages.success(request, f"Vitajte, {user.username}!")
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})

@login_required
def profile(request):
    saved_plans = SavedPlan.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'registration/profile.html', {'saved_plans': saved_plans})

@login_required
def save_current_plan(request):
    if request.method == 'POST':
        plan_name = request.POST.get('plan_name', 'Môj projekt')
        items = PlannerItem.objects.filter(user=request.user)
        if not items:
            messages.error(request, "Prázdny plánovač.")
            return redirect('planner_view')
        plan = SavedPlan.objects.create(user=request.user, name=plan_name)
        for item in items:
            SavedPlanItem.objects.create(plan=plan, product=item.product, quantity=item.quantity)
        messages.success(request, f"Projekt '{plan_name}' uložený!")
        return redirect('profile')
    return redirect('planner_view')

@login_required
def load_plan(request, plan_id):
    plan = get_object_or_404(SavedPlan, id=plan_id, user=request.user)
    PlannerItem.objects.filter(user=request.user).delete()
    for saved_item in plan.items.all():
        PlannerItem.objects.create(user=request.user, product=saved_item.product, quantity=saved_item.quantity)
    return redirect('planner_view')

@login_required
def delete_plan(request, plan_id):
    plan = get_object_or_404(SavedPlan, id=plan_id, user=request.user)
    plan.delete()
    return redirect('profile')

# ==========================================
# 6. MOJE SETY (KONFIGURÁTOR)
# ==========================================

@login_required
def my_sets_view(request):
    saved_plans = SavedPlan.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'products/my_sets.html', {'saved_plans': saved_plans})

@login_required
def save_builder_set(request):
    if request.method == 'POST':
        plan_name = request.POST.get('set_name', 'Môj nový set')
        product_ids = request.POST.getlist('product_ids') 
        if not product_ids:
            return redirect('builder')
        new_set = SavedPlan.objects.create(user=request.user, name=plan_name)
        for p_id in product_ids:
            if p_id: 
                try:
                    product = Product.objects.get(id=int(p_id))
                    SavedPlanItem.objects.create(plan=new_set, product=product, quantity=1)
                except: continue
        return redirect('my_sets')
    return redirect('builder')

@login_required
def load_set(request, set_id):
    plan = get_object_or_404(SavedPlan, id=set_id, user=request.user)
    PlannerItem.objects.filter(user=request.user).delete()
    for saved_item in plan.items.all():
        PlannerItem.objects.create(user=request.user, product=saved_item.product, quantity=saved_item.quantity)
    return redirect('planner_view')

@login_required
def delete_set(request, set_id):
    plan = get_object_or_404(SavedPlan, id=set_id, user=request.user)
    plan.delete()
    return redirect('my_sets')

# ==========================================
# 7. INTELIGENTNÝ KONFIGURÁTOR A API
# ==========================================

def builder_view(request):
    # OPRAVA: Len aktívne kategórie
    categories = Category.objects.filter(parent=None, is_active=True) 
    prefill_data = []
    bundle_slug = request.GET.get('bundle')
    if bundle_slug:
        bundle = get_object_or_404(Bundle, slug=bundle_slug)
        for i, product in enumerate(bundle.products.all()[:5]):
            prefill_data.append({
                'slot': i + 1,
                'cat_id': product.category.id if product.category else None,
                'brand': product.brand,
                'prod_id': product.id
            })
    return render(request, 'products/builder.html', {
        'categories': categories,
        'prefill_data': json.dumps(prefill_data),
        'active_bundle': bundle_slug
    })

def api_get_subcategories(request, category_id):
    """API na načítanie podkategórií pre Builder (oprava chýbajúcej funkcie)."""
    parent_category = get_object_or_404(Category, id=category_id)
    # OPRAVA: Len aktívne podkategórie
    subcategories = parent_category.children.filter(is_active=True).values('id', 'name')
    return JsonResponse({'subcategories': list(subcategories)})

def api_get_brands(request, category_id):
    # Získame značky pre kategóriu a jej deti
    products = Product.objects.filter(category_id=category_id)
    brands = set()
    for p in products:
        if p.brand: brands.add(p.brand)
        elif p.name: brands.add(p.name.split()[0])
    return JsonResponse({'brands': sorted(list(brands))})

def api_get_products(request, category_id):
    brand_name = request.GET.get('brand')
    category = get_object_or_404(Category, id=category_id)
    
    # Tu používame opravu pre podkategórie aj v API
    all_cats = [category] + get_all_children(category)
    cat_ids = [c.id for c in all_cats]
    
    products = Product.objects.filter(category_id__in=cat_ids)
    if brand_name:
        products = products.filter(brand__iexact=brand_name) | products.filter(name__istartswith=brand_name)
    
    data = []
    # Limitujeme na 50 produktov pre rýchlosť API
    for p in products[:50]:
        price = p.price if p.price > 0 else (p.offers.order_by('price').first().price if p.offers.exists() else 0)
        data.append({
            'id': p.id, 
            'name': p.name, 
            'price': str(price),
            'slug': p.slug, 
            'image': p.get_image, 
            'description': p.description[:80] + "..." if p.description else ""
        })
    return JsonResponse({'products': data})

# ==========================================
# 8. AUTOMATIZÁCIA / IMPORT
# ==========================================

def trigger_import(request):
    if not request.user.is_superuser:
        return HttpResponse("Len pre admina.", status=403)

    out = StringIO()
    sys.stdout = out
    try:
        # 1. Spustíme hlavný import
        print("--- KROK 1: IMPORT PRODUKTOV ---")
        call_command('00_import_products', stdout=out)
        
        # 2. Spustíme precízne triedenie a aktiváciu
        print("\n--- KROK 2: PRECÍZNE TRIEDENIE A AKTIVÁCIA ---")
        call_command('11_precision_sorter', stdout=out)

        result = out.getvalue()
        return HttpResponse(f"<pre>{result}</pre>", content_type="text/html")
    except Exception as e:
        return HttpResponse(f"<h1>Chyba pri importe:</h1><pre>{e}</pre>", status=500)
    finally:
        sys.stdout = sys.__stdout__