from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib.auth.models import User  # <-- TOTO JE ONO
from .models import Product, CartItem
import random

# --- POMOCNÉ FUNKCIE ---
def get_cart_products(request):
    products = []
    if request.user.is_authenticated:
        items = CartItem.objects.filter(user=request.user)
        for item in items:
            p = item.product
            p.cart_item_id = item.id 
            products.append(p)
    else:
        guest_cart = request.session.get('guest_cart', [])
        for p_id in guest_cart:
            try:
                p = Product.objects.get(id=p_id)
                p.cart_item_id = p.id 
                products.append(p)
            except Product.DoesNotExist:
                continue
    return products

# --- HLAVNÉ VIEWS ---

def home(request):
    # 1. AUTO-ADMIN: Vytvorenie superusera (Spustí sa, ak neexistuje)
    # Toto ti umožní prihlásiť sa do /admin menom 'admin' a heslom 'admin123'
    try:
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
            print("✅ Superuser 'admin' bol úspešne vytvorený!")
    except Exception as e:
        print(f"⚠️ Chyba pri vytváraní admina: {e}")

    # 2. AUTO-SEED: Ak je DB prázdna, vytvoríme produkty
    if Product.objects.count() == 0:
        sample_products = [
            ("iPhone 15 Pro", 1199.00, "iStore", "iphone"),
            ("Samsung Galaxy S24", 899.00, "Alza", "samsung-galaxy"),
            ("MacBook Air M3", 1299.00, "iStyle", "laptop"),
            ("Sony WH-1000XM5", 349.00, "Datart", "headphones"),
            ("Dyson V15 Detect", 699.00, "Nay", "vacuum-cleaner"),
            ("PlayStation 5 Slim", 549.00, "Brloh", "playstation"),
            ("GoPro HERO12", 399.00, "Alza", "camera"),
            ("iPad Air 5", 649.00, "iStore", "tablet"),
        ]
        
        for name, price, shop, category in sample_products:
            p = Product.objects.create(
                name=name,
                price=price,
                shop_name=shop,
                delivery_days=random.randint(1, 4),
                url="https://www.google.com/search?q=" + name.replace(" ", "+")
            )
            p.image_url = f"https://loremflickr.com/400/400/{category}?lock={p.id}"
            p.save()

    # 3. AUTO-FIX: Oprava obrázkov pre existujúce produkty
    for p in Product.objects.all():
        if not p.image_url or "alza" in p.image_url:
            category = "electronics"
            if "iphone" in p.name.lower(): category = "iphone"
            elif "samsung" in p.name.lower(): category = "smartphone"
            elif "macbook" in p.name.lower(): category = "laptop"
            elif "playstation" in p.name.lower(): category = "playstation"
            elif "dyson" in p.name.lower(): category = "technics"
            
            p.image_url = f"https://loremflickr.com/400/400/{category}?lock={p.id}"
            p.save()

    hladany_vyraz = request.GET.get('q')
    vsetky_produkty = Product.objects.filter(name__icontains=hladany_vyraz) if hladany_vyraz else Product.objects.all()
    
    if request.user.is_authenticated:
        pocet = CartItem.objects.filter(user=request.user).count()
    else:
        pocet = len(request.session.get('guest_cart', []))
        
    return render(request, 'products/home.html', {'produkty': vsetky_produkty, 'pocet_v_kosiku': pocet})

# --- OSTATNÉ FUNKCIE ---

def add_to_cart(request, product_id):
    if request.user.is_authenticated:
        CartItem.objects.create(user=request.user, product_id=product_id)
    else:
        cart = request.session.get('guest_cart', [])
        cart.append(product_id)
        request.session['guest_cart'] = cart
        request.session.modified = True
    return redirect('home')

def remove_from_cart(request, item_id):
    if request.user.is_authenticated:
        get_object_or_404(CartItem, id=item_id, user=request.user).delete()
    else:
        cart = request.session.get('guest_cart', [])
        if item_id in cart:
            cart.remove(item_id)
            request.session['guest_cart'] = cart
            request.session.modified = True
    return redirect('cart_detail')

def cart_detail(request):
    items = get_cart_products(request)
    formatted_items = [{'product': p, 'id': p.cart_item_id} for p in items]
    return render(request, 'products/cart.html', {'items': formatted_items})

def optimize_cart(request):
    moj_kosik = get_cart_products(request)
    if not moj_kosik: return redirect('home')
    
    baliky = {}
    suma_tovaru = 0
    zoznam_mien = {}
    
    for p in moj_kosik:
        meno = p.name.strip().lower()
        kluc = meno.split()[0]
        zoznam_mien[kluc] = zoznam_mien.get(kluc, 0) + 1
        
        if p.shop_name not in baliky:
            baliky[p.shop_name] = {'produkty': [], 'cena_tovaru': 0, 'postovne': 3.90}
        baliky[p.shop_name]['produkty'].append(p)
        baliky[p.shop_name]['cena_tovaru'] += float(p.price)
        suma_tovaru += float(p.price)
        
    aktualna_celkova = suma_tovaru + (len(baliky) * 3.90)
    
    lepsia_alternativa = None
    najlepšia_nova_suma = aktualna_celkova
    vsetky_shopy = Product.objects.values_list('shop_name', flat=True).distinct()
    
    for shop in vsetky_shopy:
        suma_v_shope = 0
        nasli_sme_vsetko = True
        for kluc_produkt, pocet in zoznam_mien.items():
            p_alt = Product.objects.filter(name__icontains=kluc_produkt, shop_name=shop).first()
            if p_alt: suma_v_shope += float(p_alt.price) * pocet
            else:
                nasli_sme_vsetko = False
                break
        
        if nasli_sme_vsetko:
            nova_suma = suma_v_shope + 3.90
            if nova_suma < najlepšia_nova_suma:
                najlepšia_nova_suma = nova_suma
                lepsia_alternativa = {'obchod': shop, 'nova_cena': round(nova_suma, 2), 'uspora': round(aktualna_celkova - nova_suma, 2)}
                
    return render(request, 'products/optimization_result.html', {
        'baliky': baliky, 'celkova_cena_tovaru': round(suma_tovaru, 2),
        'celkove_postovne': round(len(baliky) * 3.90, 2), 'celkova_suma': round(aktualna_celkova, 2),
        'lepsia_alternativa': lepsia_alternativa
    })

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            guest_cart = request.session.get('guest_cart', [])
            if guest_cart:
                for product_id in guest_cart:
                    CartItem.objects.create(user=user, product_id=product_id)
                del request.session['guest_cart']
                request.session.modified = True
            login(request, user)
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})

def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    if request.user.is_authenticated:
        pocet_v_kosiku = CartItem.objects.filter(user=request.user).count()
    else:
        pocet_v_kosiku = len(request.session.get('guest_cart', []))
    
    seo_description = f"Najlepšia cena pre {product.name}. Kúpte výhodne od predajcu {product.shop_name} za {product.price} €."
    
    klucove_slovo = product.name.split()[0]
    podobne_produkty = Product.objects.filter(name__icontains=klucove_slovo).exclude(id=product.id)[:4]

    return render(request, 'products/product_detail.html', {
        'p': product,
        'pocet_v_kosiku': pocet_v_kosiku,
        'seo_description': seo_description,
        'podobne_produkty': podobne_produkty
    })