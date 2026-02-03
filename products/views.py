from django.shortcuts import render, redirect, get_object_or_404
from .models import Product, Category, Offer, PlannerItem, Bundle, SavedPlan, SavedPlanItem, Review
from .forms import ReviewForm  # <--- NOVÝ IMPORT (Formulár pre recenzie)
from django.db.models import Min, Q, Sum, Max # <--- PRIDANÉ Max PRE TRIEDENIE SPONZOROVANÝCH
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

# ==========================================
# 1. HLAVNÉ STRÁNKY
# ==========================================

def home(request):
    """Domovská stránka s produktami, balíčkami a kategóriami."""
    # Optimalizácia: Načítame len hlavné kategórie (rodičov)
    all_categories = Category.objects.filter(parent=None)
    
    products = Product.objects.order_by('-created_at')[:8]
    
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
    category = get_object_or_404(Category, slug=slug)
    
    # Hľadáme produkty v tejto kategórii ALEBO v jej podkategóriách
    products = Product.objects.filter(
        Q(category=category) | Q(category__parent=category)
    ).distinct()

    sort_by = request.GET.get('sort', 'default') # Zmenil som default na 'default'
    
    # --- LOGIKA TRIEDENIA (ZJEDNODUŠENÁ - BEZPEČNÁ) ---
    if sort_by == 'price_asc':
        products = products.order_by('price')
    elif sort_by == 'price_desc':
        products = products.order_by('-price')
    elif sort_by == 'name':
        products = products.order_by('name')
    else:
        # Bezpečný fallback: najnovšie produkty prvé
        # Vyhodil som to rizikové 'recommended' s annotate, kým sa DB nestabilizuje
        products = products.order_by('-created_at')
    
    # Bočný panel - len hlavné kategórie
    all_categories = Category.objects.filter(parent=None)

    return render(request, 'products/category_detail.html', {
        'category': category,
        'products': products,
        'all_categories': all_categories,
        'sort_by': sort_by
    })

def search(request):
    """Vyhľadávanie produktov."""
    query = request.GET.get('q')
    results = []
    
    if query:
        results = Product.objects.filter(
            Q(name__icontains=query) | 
            Q(description__icontains=query) |
            Q(ean__icontains=query) |
            Q(category__name__icontains=query)
        ).distinct()
    
    return render(request, 'products/search.html', {'products': results, 'query': query})

def privacy_policy(request):
    return render(request, 'pages/gdpr.html')

# ==========================================
# 2. DETAIL PRODUKTU (S RECENZIAMI)
# ==========================================

def product_detail(request, slug): 
    product = get_object_or_404(Product, slug=slug)
    
    # Zoradíme ponuky: Sponzorované prvé (True > False), potom najlacnejšie
    offers = product.offers.filter(active=True).order_by('-is_sponsored', 'price')
    
    # --- SPRACOVANIE RECENZIE ---
    if request.method == 'POST' and request.user.is_authenticated:
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.product = product
            review.user = request.user
            review.save()
            messages.success(request, "Ďakujeme za vaše hodnotenie!")
            return redirect('product_detail', slug=slug)
    else:
        form = ReviewForm()

    history = product.price_history.all()
    dates = [h.date.strftime("%d.%m.") for h in history]
    min_prices = [float(h.min_price) for h in history]
    avg_prices = [float(h.avg_price) for h in history]
    
    return render(request, 'products/product_detail.html', {
        'product': product, 
        'offers': offers,
        'form': form,   # Formulár pre novú recenziu
        'reviews': product.reviews.all(), # Zoznam existujúcich recenzií
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
    if request.user.is_authenticated:
        items = PlannerItem.objects.filter(user=request.user)
    else:
        items = PlannerItem.objects.filter(session_key=get_session_key(request))
    
    total_estimated = 0
    for item in items:
        price = item.product.price
        if price == 0:
            cheapest = item.product.offers.filter(active=True).order_by('price').first()
            if cheapest:
                price = cheapest.price
        
        total_estimated += price * item.quantity

    return render(request, 'products/planner.html', {'items': items, 'total_price': total_estimated})

# ==========================================
# 4. SMART POROVNANIE
# ==========================================

def comparison(request):
    if request.user.is_authenticated:
        items = PlannerItem.objects.filter(user=request.user)
    else:
        items = PlannerItem.objects.filter(session_key=get_session_key(request))

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
            if item.product.is_oversized:
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
                if item.product.is_oversized:
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

            messages.success(request, f"Vitajte, {user.username}! Vaše produkty boli prenesené.")
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})

@login_required
def profile(request):
    saved_plans = SavedPlan.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'registration/profile.html', {'saved_plans': saved_plans})

# --- STARÉ FUNKCIE PRE UKLADANIE KOŠÍKA ---
@login_required
def save_current_plan(request):
    if request.method == 'POST':
        plan_name = request.POST.get('plan_name', 'Môj projekt')
        items = PlannerItem.objects.filter(user=request.user)
        if not items:
            messages.error(request, "Váš plánovač je prázdny.")
            return redirect('planner_view')
        plan = SavedPlan.objects.create(user=request.user, name=plan_name)
        for item in items:
            SavedPlanItem.objects.create(plan=plan, product=item.product, quantity=item.quantity)
        messages.success(request, f"Projekt '{plan_name}' bol uložený!")
        return redirect('profile')
    return redirect('planner_view')

@login_required
def load_plan(request, plan_id):
    plan = get_object_or_404(SavedPlan, id=plan_id, user=request.user)
    PlannerItem.objects.filter(user=request.user).delete()
    for saved_item in plan.items.all():
        PlannerItem.objects.create(user=request.user, product=saved_item.product, quantity=saved_item.quantity)
    messages.success(request, f"Projekt '{plan.name}' bol načítaný.")
    return redirect('planner_view')

@login_required
def delete_plan(request, plan_id):
    plan = get_object_or_404(SavedPlan, id=plan_id, user=request.user)
    plan.delete()
    messages.success(request, "Projekt vymazaný.")
    return redirect('profile')

# ==========================================
# 6. NOVÉ: MOJE SETY (GARÁŽ)
# ==========================================

@login_required
def my_sets_view(request):
    """Zobrazí zoznam uložených setov z konfigurátora."""
    saved_plans = SavedPlan.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'products/my_sets.html', {'saved_plans': saved_plans})

@login_required
def save_builder_set(request):
    """Uloží produkty z konfigurátora ako nový set."""
    if request.method == 'POST':
        plan_name = request.POST.get('set_name', 'Môj nový set')
        product_ids = request.POST.getlist('product_ids') 

        if not product_ids:
            messages.error(request, "Set je prázdny, vyberte aspoň jeden produkt.")
            return redirect('builder')

        new_set = SavedPlan.objects.create(user=request.user, name=plan_name)
        
        count = 0
        for p_id in product_ids:
            if p_id: 
                try:
                    product = Product.objects.get(id=p_id)
                    SavedPlanItem.objects.create(plan=new_set, product=product, quantity=1)
                    count += 1
                except Product.DoesNotExist:
                    continue
        
        if count > 0:
            messages.success(request, f"Set '{plan_name}' bol úspešne uložený!")
            return redirect('my_sets')
        else:
            new_set.delete()
            messages.error(request, "Nepodarilo sa uložiť žiadne produkty.")
            
    return redirect('builder')

@login_required
def load_set(request, set_id):
    """Načíta vybraný set do aktuálneho košíka."""
    plan = get_object_or_404(SavedPlan, id=set_id, user=request.user)
    
    PlannerItem.objects.filter(user=request.user).delete()
    
    for saved_item in plan.items.all():
        PlannerItem.objects.create(
            user=request.user,
            product=saved_item.product,
            quantity=saved_item.quantity
        )
        
    messages.success(request, f"Set '{plan.name}' bol presunutý do nákupného zoznamu.")
    return redirect('planner_view')

@login_required
def delete_set(request, set_id):
    """Vymaže set zo stránky Moje sety."""
    plan = get_object_or_404(SavedPlan, id=set_id, user=request.user)
    plan.delete()
    messages.success(request, "Set bol vymazaný.")
    return redirect('my_sets')

# ==========================================
# 7. INTELIGENTNÝ KONFIGURÁTOR
# ==========================================

def builder_view(request):
    categories = Category.objects.filter(parent=None) 
    
    prefill_data = []
    bundle_slug = request.GET.get('bundle')
    
    if bundle_slug:
        bundle = get_object_or_404(Bundle, slug=bundle_slug)
        products = bundle.products.all()[:5]
        
        for i, product in enumerate(products):
            prefill_data.append({
                'slot': i + 1,
                'cat_id': product.category.id,
                'brand': product.brand,
                'prod_id': product.id
            })
            
    return render(request, 'products/builder.html', {
        'categories': categories,
        'prefill_data': json.dumps(prefill_data),
        'active_bundle': bundle_slug
    })

def api_get_brands(request, category_id):
    products = Product.objects.filter(category_id=category_id)
    
    brands = set()
    for p in products:
        if p.brand:
            brands.add(p.brand)
        else:
            brands.add(p.name.split()[0])
            
    return JsonResponse({'brands': sorted(list(brands))})

def api_get_products(request, category_id):
    brand_name = request.GET.get('brand')
    products = Product.objects.filter(category_id=category_id)
    
    if brand_name:
        products = products.filter(brand__iexact=brand_name) | products.filter(name__istartswith=brand_name)
        
    data = []
    for p in products:
        price = p.price
        if price == 0:
            lowest_offer = p.offers.order_by('price').first()
            price = lowest_offer.price if lowest_offer else 0
        
        short_desc = p.description[:80] + "..." if p.description else "Bez popisu."
        
        data.append({
            'id': p.id,
            'name': p.name,
            'price': str(price),
            'slug': p.slug,
            'image': p.image_url,
            'description': short_desc
        })
        
    return JsonResponse({'products': data})

# ==========================================
# 8. AUTOMATIZÁCIA / IMPORT
# ==========================================

def trigger_import(request):
    if not request.user.is_superuser:
        return HttpResponse("Len pre administrátora.", status=403)

    out = StringIO()
    sys.stdout = out
    try:
        try:
            from generate_xml import generate_feed
            generate_feed()
            print("✅ XML vygenerované.", file=out)
        except ImportError:
            print("⚠️ generate_xml.py nenájdený, preskakujem generovanie XML.", file=out)

        call_command('import_real_xml', stdout=out)
        result = out.getvalue()
        return HttpResponse(f"<pre>{result}</pre>", content_type="text/html")
    except Exception as e:
        return HttpResponse(f"<h1>Chyba pri importe:</h1><pre>{e}</pre>", status=500)
    finally:
        sys.stdout = sys.__stdout__