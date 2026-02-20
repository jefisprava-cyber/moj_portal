from django.shortcuts import render, redirect, get_object_or_404
from .models import Product, Category, Offer, PlannerItem, Bundle, SavedPlan, SavedPlanItem, Review
from .forms import ReviewForm
from django.db.models import Min, Q, Sum, Max, Prefetch, Case, When, Value, IntegerField
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.core.management import call_command
# 👇 OPRAVA 1: Import pre Cache pamäť
from django.core.cache import cache
import json 
import sys
from io import StringIO

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

def get_all_children(category):
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

# 👇 OPRAVA 2: Funkcia, ktorá drží menu v rýchlej pamäti 24 hodín
def get_cached_categories():
    """Získa hlavné kategórie z rýchlej pamäte (Cache), aby sa nezaťažovala databáza."""
    categories = cache.get('all_main_categories')
    if not categories:
        # Ak menu nie je v pamäti, stiahneme ho a uložíme na 86400 sekúnd (24 hodín)
        categories = Category.objects.filter(parent=None, is_active=True).prefetch_related('children')
        cache.set('all_main_categories', categories, 86400)
    return categories

# ==========================================
# 1. HLAVNÉ STRÁNKY
# ==========================================

def home(request):
    # 👇 OPRAVA 3: Použijeme rýchlu pamäť namiesto databázy
    all_categories = get_cached_categories()
    
    products = Product.objects.filter(category__is_active=True)\
        .select_related('category')\
        .prefetch_related('offers')\
        .order_by('-created_at')[:12] 

    bundles = Bundle.objects.all().prefetch_related('products')
    
    cart_count = 0
    if request.user.is_authenticated:
        cart_count = PlannerItem.objects.filter(user=request.user).count()
    elif request.session.session_key:
        cart_count = PlannerItem.objects.filter(session_key=get_session_key(request)).count()

    return render(request, 'products/home.html', {
        'products': products,
        'bundles': bundles,
        'cart_count': cart_count,
        'all_categories': all_categories
    })

def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug, is_active=True)
    
    cat_ids = [category.id]
    child_ids = Category.objects.filter(parent=category, is_active=True).values_list('id', flat=True)
    cat_ids.extend(child_ids)
    
    grandchild_ids = Category.objects.filter(parent_id__in=child_ids, is_active=True).values_list('id', flat=True)
    cat_ids.extend(grandchild_ids)

    products = Product.objects.filter(
        category_id__in=cat_ids
    ).select_related('category').prefetch_related('offers')

    sort_by = request.GET.get('sort', 'default')
    if sort_by == 'price_asc':
        products = products.order_by('price')
    elif sort_by == 'price_desc':
        products = products.order_by('-price')
    elif sort_by == 'name':
        products = products.order_by('name')
    else:
        products = products.order_by('-created_at')
    
    products = products[:24]
    
    # 👇 Použitie Cache
    all_categories = get_cached_categories()

    return render(request, 'products/category_detail.html', {
        'category': category,
        'products': products,
        'all_categories': all_categories,
        'sort_by': sort_by
    })

def search(request):
    """Vyhľadávanie produktov - TOP RELEVANCIA + SLOVENČINA"""
    query = request.GET.get('q', '').strip()
    results = Product.objects.none()
    error_message = None
    
    if len(query) < 3:
        if query: 
            error_message = "Zadajte aspoň 3 znaky."
    else:
        matching_categories = list(Category.objects.filter(
            name__icontains=query, 
            is_active=True
        ).values_list('id', flat=True))

        active_cat_ids = list(Category.objects.filter(is_active=True).values_list('id', flat=True))
        
        q_lower = query.lower()
        alt_query = query 
        
        name_filters = Q(name__icontains=query)
        
        if "stol" in q_lower: 
            alt_query = q_lower.replace("stol", "stôl")
            name_filters |= Q(name__icontains=alt_query)
        elif "skrin" in q_lower: 
            alt_query = q_lower.replace("skrin", "skriň")
            name_filters |= Q(name__icontains=alt_query)
        elif "postel" in q_lower: 
            alt_query = q_lower.replace("postel", "posteľ")
            name_filters |= Q(name__icontains=alt_query)

        results = Product.objects.filter(
            category_id__in=active_cat_ids
        ).filter(
            name_filters | 
            Q(ean__icontains=query) |
            Q(category_id__in=matching_categories)
        ).annotate(
            relevance=Case(
                When(name__iexact=query, then=Value(1)),
                When(name__iexact=alt_query, then=Value(1)),
                When(name__istartswith=f"{query} ", then=Value(2)),
                When(name__istartswith=f"{alt_query} ", then=Value(2)),
                When(name__icontains=f" {query} ", then=Value(3)),
                When(name__icontains=f" {alt_query} ", then=Value(3)),
                When(name__endswith=f" {query}", then=Value(4)),
                When(name__endswith=f" {alt_query}", then=Value(4)),
                When(name__istartswith=query, then=Value(5)),
                When(name__istartswith=alt_query, then=Value(5)),
                When(name__icontains=query, then=Value(6)),
                When(name__icontains=alt_query, then=Value(6)),
                When(ean__icontains=query, then=Value(7)),
                default=Value(8),
                output_field=IntegerField(),
            )
        ).select_related('category').prefetch_related('offers').order_by('relevance', '-created_at')[:50]
    
    # 👇 Použitie Cache
    all_categories = get_cached_categories()

    return render(request, 'products/search_results.html', {
        'products': results, 
        'search_query': query,
        'all_categories': all_categories,
        'is_search': True,
        'error_message': error_message
    })

def privacy_policy(request):
    return render(request, 'pages/gdpr.html')

# ==========================================
# 2. DETAIL PRODUKTU (S RECENZIAMI)
# ==========================================

def product_detail(request, slug): 
    product = get_object_or_404(Product.objects.prefetch_related('offers', 'reviews', 'price_history'), slug=slug)
    
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

    history = product.price_history.all()
    dates = [h.date.strftime("%d.%m.") for h in history]
    min_prices = [float(h.min_price) for h in history]
    avg_prices = [float(h.avg_price) for h in history]
    
    return render(request, 'products/product_detail.html', {
        'product': product, 
        'offers': offers,
        'form': form,
        'reviews': product.reviews.all(), 
        'chart_dates': json.dumps(dates),
        'chart_min_prices': json.dumps(min_prices),
        'chart_avg_prices': json.dumps(avg_prices)
    })

def bundle_detail(request, bundle_slug):
    bundle = get_object_or_404(Bundle.objects.prefetch_related('products__offers'), slug=bundle_slug)
    products = bundle.products.all()
    total_price = 0
    for p in products:
        if p.price > 0:
            total_price += p.price
        else:
            offer = p.offers.filter(active=True).order_by('price').first()
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
    bundle = get_object_or_404(Bundle.objects.prefetch_related('products'), id=bundle_id)
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
    queryset = PlannerItem.objects.select_related('product').prefetch_related('product__offers')

    if request.user.is_authenticated:
        items = queryset.filter(user=request.user)
    else:
        items = queryset.filter(session_key=get_session_key(request))
    
    total_estimated = 0
    for item in items:
        cheapest = item.product.offers.filter(active=True).order_by('price').first()
        item.cheapest_offer = cheapest

        price = item.product.price
        if price == 0 and cheapest:
            price = cheapest.price
        
        total_estimated += price * item.quantity

    return render(request, 'products/planner.html', {'items': items, 'total_price': total_estimated})

# ==========================================
# 4. SMART POROVNANIE
# ==========================================

def comparison(request):
    queryset = PlannerItem.objects.select_related('product').prefetch_related('product__offers')

    if request.user.is_authenticated:
        items = queryset.filter(user=request.user)
    else:
        items = queryset.filter(session_key=get_session_key(request))

    if not items:
        return redirect('home')
    
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

    all_offers = []
    for item in items:
        all_offers.extend(item.product.offers.all())
    
    shop_names = set(o.shop_name for o in all_offers if o.active)
    
    single_shop_results = []

    for shop in shop_names:
        shop_items_cost = 0
        shop_has_oversized = False
        found_all = True
        
        for item in items:
            offer = next((o for o in item.product.offers.all() if o.shop_name == shop and o.active), None)
            
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
    # 👇 Použitie Cache
    categories = get_cached_categories()
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
    """API na načítanie podkategórií pre Builder."""
    parent_category = get_object_or_404(Category, id=category_id)
    subcategories = parent_category.children.filter(is_active=True).values('id', 'name')
    return JsonResponse({'subcategories': list(subcategories)})

def api_get_brands(request, category_id):
    all_cats = [category_id] 
    brands = Product.objects.filter(category_id__in=all_cats).values_list('brand', flat=True).distinct().order_by('brand')
    clean_brands = [b for b in brands if b]
    return JsonResponse({'brands': clean_brands})

def api_get_products(request, category_id):
    brand_name = request.GET.get('brand')
    category = get_object_or_404(Category, id=category_id)
    
    all_cats = [category] + get_all_children(category)
    cat_ids = [c.id for c in all_cats]
    
    queryset = Product.objects.filter(category_id__in=cat_ids).prefetch_related('offers')
    
    if brand_name:
        queryset = queryset.filter(brand__iexact=brand_name) | queryset.filter(name__istartswith=brand_name)
    
    data = []
    for p in queryset[:50]:
        offer = p.offers.filter(active=True).order_by('price').first()
        price = p.price if p.price > 0 else (offer.price if offer else 0)
        
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
        print("--- KROK 1: IMPORT PRODUKTOV ---")
        call_command('00_import_products', stdout=out)
        
        print("\n--- KROK 2: PRECÍZNE TRIEDENIE A AKTIVÁCIA ---")
        call_command('11_precision_sorter', stdout=out)

        result = out.getvalue()
        return HttpResponse(f"<pre>{result}</pre>", content_type="text/html")
    except Exception as e:
        return HttpResponse(f"<h1>Chyba pri importe:</h1><pre>{e}</pre>", status=500)
    finally:
        sys.stdout = sys.__stdout__