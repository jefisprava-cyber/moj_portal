from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from .models import Category, Product, Offer, CartItem, Order, OrderItem
from .forms import OrderForm
from django.contrib import messages
from django.db.models import Min
import random

# --- CENNÍK DOPRAVY ---
SHIPPING_PRICES = {
    "Alza": 4.90, "iStore": 5.00, "iStyle": 5.50,
    "Nay": 3.90, "Datart": 3.90, "Brloh": 4.50,
}
DEFAULT_SHIPPING = 3.90

def get_shipping_cost(shop_name):
    return SHIPPING_PRICES.get(shop_name, DEFAULT_SHIPPING)

def get_cart_offers(request):
    offers = []
    if request.user.is_authenticated:
        items = CartItem.objects.filter(user=request.user)
        for item in items:
            o = item.offer
            o.cart_item_id = item.id
            offers.append(o)
    else:
        guest_cart = request.session.get('guest_cart', [])
        for offer_id in guest_cart:
            try:
                o = Offer.objects.get(id=offer_id)
                o.cart_item_id = o.id
                offers.append(o)
            except Offer.DoesNotExist: continue
    return offers

# --- HLAVNÁ STRÁNKA ---

def home(request):
    # 1. AUTO-ADMIN (Vytvorí sa len ak neexistuje)
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@example.com', 'admin123')

    # 2. AUTO-SEED (Bezpečné generovanie dát)
    if Category.objects.count() == 0:
        # Hlavná kategória
        cat_elek, _ = Category.objects.get_or_create(name="Elektronika", slug="elektronika")
        
        # Podkategórie
        sub_mobily, _ = Category.objects.get_or_create(name="Smartfóny", slug="smartfony", parent=cat_elek)
        sub_laptopy, _ = Category.objects.get_or_create(name="Notebooky", slug="notebooky", parent=cat_elek)
        sub_audio, _ = Category.objects.get_or_create(name="Audio", slug="audio", parent=cat_elek)
        sub_wear, _ = Category.objects.get_or_create(name="Smart Hodinky", slug="hodinky", parent=cat_elek)

        # Produkty
        products_map = [
            ("iPhone 15 Pro", sub_mobily, "iphone"),
            ("Samsung Galaxy S24", sub_mobily, "samsung-phone"),
            ("MacBook Air M3", sub_laptopy, "macbook"),
            ("Sony WH-1000XM5", sub_audio, "headphones"),
            ("Apple Watch 9", sub_wear, "apple-watch"),
        ]
        
        shops = ["Alza", "Nay", "iStyle", "Datart"]
        
        for name, cat, img_key in products_map:
            p, created = Product.objects.get_or_create(name=name, category=cat)
            if created:
                p.image_url = f"https://loremflickr.com/500/500/{img_key}?lock={random.randint(1,500)}"
                p.save()
                
                # Ponuky
                chosen_shops = random.sample(shops, 3)
                base_price = random.randint(300, 1200)
                for shop in chosen_shops:
                    Offer.objects.create(
                        product=p,
                        shop_name=shop,
                        price=base_price + random.randint(-50, 50),
                        delivery_days=random.randint(1, 5),
                        url="https://google.com"
                    )

    # 3. PRÍPRAVA DÁT (Kritická časť)
    
    # a) Načítanie kategórií do stromovej štruktúry (Parent -> Children)
    # Toto zabezpečí, že sa v šablóne nepomýlime
    root_categories = Category.objects.filter(parent=None).prefetch_related('children')
    
    # b) Filtrovanie produktov
    active_category = None
    produkty = Product.objects.all()
    
    category_slug = request.GET.get('category')
    query = request.GET.get('q')

    if category_slug:
        active_category = get_object_or_404(Category, slug=category_slug)
        # Získame ID kategórie aj jej detí
        cat_ids = [active_category.id] + list(active_category.children.values_list('id', flat=True))
        produkty = produkty.filter(category__id__in=cat_ids)

    if query:
        produkty = produkty.filter(name__icontains=query)

    # c) Výpočet cien pre zobrazenie
    for p in produkty:
        cheapest = p.offers.order_by('price').first()
        p.price_display = cheapest.price if cheapest else 0
        p.shop_display = cheapest.shop_name if cheapest else ""
        p.delivery_display = cheapest.delivery_days if cheapest else 0
        p.best_offer_id = cheapest.id if cheapest else None

    pocet = CartItem.objects.filter(user=request.user).count() if request.user.is_authenticated else len(request.session.get('guest_cart', []))
    
    context = {
        'root_categories': root_categories, # Posielame už pripravené stromy
        'produkty': produkty,
        'active_category': active_category,
        'pocet_v_kosiku': pocet,
        'query': query
    }
    
    return render(request, 'products/home.html', context)

# --- OSTATNÉ FUNKCIE (Bez zmeny) ---
def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    offers = product.offers.all().order_by('price')
    pocet = CartItem.objects.filter(user=request.user).count() if request.user.is_authenticated else len(request.session.get('guest_cart', []))
    return render(request, 'products/product_detail.html', {'p': product, 'offers': offers, 'pocet_v_kosiku': pocet})

def add_to_cart(request, offer_id): 
    if request.user.is_authenticated:
        CartItem.objects.create(user=request.user, offer_id=offer_id)
    else:
        cart = request.session.get('guest_cart', [])
        cart.append(offer_id)
        request.session['guest_cart'] = cart
        request.session.modified = True
    messages.success(request, "Produkt bol pridaný do košíka")
    return redirect('home')

def remove_from_cart(request, item_id):
    if request.user.is_authenticated:
        get_object_or_404(CartItem, id=item_id, user=request.user).delete()
    else:
        cart = request.session.get('guest_cart', [])
        try: item_id = int(item_id)
        except: pass
        if item_id in cart: 
            cart.remove(item_id)
            request.session['guest_cart'] = cart
            request.session.modified = True
    return redirect('cart_detail')

def cart_detail(request):
    offers = get_cart_offers(request)
    formatted = [{'offer': o, 'id': o.cart_item_id} for o in offers]
    pocet = len(formatted)
    return render(request, 'products/cart.html', {'items': formatted, 'pocet_v_kosiku': pocet})

def optimize_cart(request):
    cart_offers = get_cart_offers(request)
    if not cart_offers: return redirect('home')
    baliky = {}
    total_goods = 0
    total_shipping = 0
    max_days_orig = 0
    for o in cart_offers:
        shop = o.shop_name
        if shop not in baliky:
            shipping = get_shipping_cost(shop)
            baliky[shop] = {'produkty': [], 'cena_tovaru': 0, 'postovne': shipping}
            total_shipping += shipping
        baliky[shop]['produkty'].append(o)
        baliky[shop]['cena_tovaru'] += float(o.price)
        total_goods += float(o.price)
        if o.delivery_days > max_days_orig: max_days_orig = o.delivery_days
    current_total = total_goods + total_shipping
    required_products = list(set([o.product for o in cart_offers]))
    all_shops = Offer.objects.values_list('shop_name', flat=True).distinct()
    best_alt = None
    best_price = current_total
    for shop in all_shops:
        shop_total_price = 0
        shop_max_days = 0
        found_all = True
        for prod in required_products:
            offer = prod.offers.filter(shop_name=shop).first()
            if offer:
                shop_total_price += float(offer.price)
                if offer.delivery_days > shop_max_days: shop_max_days = offer.delivery_days
            else:
                found_all = False
                break
        if found_all:
            shipping = get_shipping_cost(shop)
            final_shop_price = shop_total_price + shipping
            if final_shop_price <= current_total:
                if final_shop_price < best_price or best_alt is None:
                    best_price = final_shop_price
                    best_alt = {'obchod': shop, 'nova_cena': round(final_shop_price, 2), 'uspora': round(current_total - final_shop_price, 2), 'dni_dorucenia': shop_max_days}
    return render(request, 'products/optimization_result.html', {
        'baliky': baliky,
        'celkova_cena_tovaru': round(total_goods, 2),
        'celkove_postovne': round(total_shipping, 2),
        'celkova_suma': round(current_total, 2),
        'max_dni_povodna': max_days_orig,
        'lepsia_alternativa': best_alt
    })

def checkout(request):
    cart_offers = get_cart_offers(request)
    if not cart_offers: return redirect('home')
    is_optimized = request.GET.get('optimized') == 'true'
    target_shop = request.GET.get('shop')
    final_offers = []
    if is_optimized and target_shop:
        required_products = set([o.product for o in cart_offers])
        for prod in required_products:
            alt = prod.offers.filter(shop_name=target_shop).first()
            final_offers.append(alt if alt else cart_offers[0]) 
    else:
        final_offers = cart_offers
    goods_price = sum(float(o.price) for o in final_offers)
    shops = set(o.shop_name for o in final_offers)
    shipping = sum(get_shipping_cost(s) for s in shops)
    grand_total = goods_price + shipping
    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            if request.user.is_authenticated: order.user = request.user
            order.total_price = grand_total
            if is_optimized: order.note = f"[CESTA B - {target_shop}] " + (order.note or "")
            order.save()
            for o in final_offers:
                OrderItem.objects.create(order=order, offer=o, price=o.price, quantity=1)
            if request.user.is_authenticated: CartItem.objects.filter(user=request.user).delete()
            else: 
                if 'guest_cart' in request.session: del request.session['guest_cart']
                request.session.modified = True
            return render(request, 'products/order_success.html', {'order': order})
    else:
        form = OrderForm(initial={'email': request.user.email} if request.user.is_authenticated else {})
    return render(request, 'products/checkout.html', {
        'form': form, 'cart_items': final_offers, 
        'total_price': round(grand_total, 2), 'is_optimized': is_optimized
    })

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            guest_cart = request.session.get('guest_cart', [])
            for oid in guest_cart: CartItem.objects.create(user=user, offer_id=oid)
            if 'guest_cart' in request.session: del request.session['guest_cart']
            login(request, user)
            return redirect('home')
    else: form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})