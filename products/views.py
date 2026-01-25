from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from .models import Product, CartItem

# POMOCNÁ FUNKCIA: Získa produkty pre košík (spoločné pre zobrazenie aj optimalizáciu)
def get_cart_products(request):
    products = []
    if request.user.is_authenticated:
        items = CartItem.objects.filter(user=request.user)
        for item in items:
            # Uložíme si aj ID záznamu v DB, aby fungovalo mazanie
            p = item.product
            p.cart_item_id = item.id 
            products.append(p)
    else:
        # Pre hostí berieme ID produktov zo Session
        guest_cart = request.session.get('guest_cart', [])
        for p_id in guest_cart:
            p = get_object_or_404(Product, id=p_id)
            # Pre hostí použijeme produkt ID ako cart_item_id
            p.cart_item_id = p.id 
            products.append(p)
    return products

# 1. HLAVNÁ STRÁNKA
def home(request):
    hladany_vyraz = request.GET.get('q')
    vsetky_produkty = Product.objects.filter(name__icontains=hladany_vyraz) if hladany_vyraz else Product.objects.all()
    
    # Počítanie kusov (DB + Session)
    if request.user.is_authenticated:
        pocet = CartItem.objects.filter(user=request.user).count()
    else:
        pocet = len(request.session.get('guest_cart', []))
        
    return render(request, 'products/home.html', {'produkty': vsetky_produkty, 'pocet_v_kosiku': pocet})

# 2. PRIDANIE DO KOŠÍKA (Už nepotrebuje login)
def add_to_cart(request, product_id):
    if request.user.is_authenticated:
        CartItem.objects.create(user=request.user, product_id=product_id)
    else:
        # Uložíme do "pamäte" prehliadača
        cart = request.session.get('guest_cart', [])
        cart.append(product_id)
        request.session['guest_cart'] = cart
        request.session.modified = True
    return redirect('home')

# 3. ZMAZANIE Z KOŠÍKA
def remove_from_cart(request, item_id):
    if request.user.is_authenticated:
        get_object_or_404(CartItem, id=item_id, user=request.user).delete()
    else:
        # Odstránime jedno ID zo zoznamu v Session
        cart = request.session.get('guest_cart', [])
        if item_id in cart:
            cart.remove(item_id)
            request.session['guest_cart'] = cart
            request.session.modified = True
    return redirect('cart_detail')

# 4. ZOBRAZENIE KOŠÍKA
def cart_detail(request):
    items = get_cart_products(request)
    # Naformátujeme to pre šablónu, aby "p.product" stále fungovalo
    formatted_items = [{'product': p, 'id': p.cart_item_id} for p in items]
    return render(request, 'products/cart.html', {'items': formatted_items})

# 5. OPTIMALIZÁTOR
def optimize_cart(request):
    moj_kosik = get_cart_products(request)
    if not moj_kosik: 
        return redirect('home')

    baliky = {}
    suma_tovaru = 0
    zoznam_mien = {}

    for p in moj_kosik:
        meno = p.name.strip().lower()
        zoznam_mien[meno] = zoznam_mien.get(meno, 0) + 1
        
        if p.shop_name not in baliky:
            baliky[p.shop_name] = {'produkty': [], 'cena_tovaru': 0, 'postovne': 3.90}
        baliky[p.shop_name]['produkty'].append(p)
        baliky[p.shop_name]['cena_tovaru'] += float(p.price)
        suma_tovaru += float(p.price)

    aktualna_celkova = suma_tovaru + (len(baliky) * 3.90)

    # HĽADANIE ALTERNATÍVY (logika ostáva rovnaká)
    lepsia_alternativa = None
    najlepšia_nova_suma = aktualna_celkova
    vsetky_shopy = Product.objects.values_list('shop_name', flat=True).distinct()

    for shop in vsetky_shopy:
        suma_v_shope = 0
        nasli_sme_vsetko = True
        for meno_produkt, pocet in zoznam_mien.items():
            p_alt = Product.objects.filter(name__iexact=meno_produkt, shop_name=shop).first()
            if p_alt:
                suma_v_shope += float(p_alt.price) * pocet
            else:
                nasli_sme_vsetko = False
                break
        
        if nasli_sme_vsetko:
            nova_suma = suma_v_shope + 3.90
            if nova_suma < najlepšia_nova_suma:
                najlepšia_nova_suma = nova_suma
                lepsia_alternativa = {
                    'obchod': shop,
                    'nova_cena': round(nova_suma, 2),
                    'uspora': round(aktualna_celkova - nova_suma, 2)
                }

    return render(request, 'products/optimization_result.html', {
        'baliky': baliky,
        'celkova_cena_tovaru': round(suma_tovaru, 2),
        'celkove_postovne': round(len(baliky) * 3.90, 2),
        'celkova_suma': round(aktualna_celkova, 2),
        'lepsia_alternativa': lepsia_alternativa
    })

# 6. REGISTRÁCIA S PRELIATÍM KOŠÍKA
def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # --- LOGIKA PRELIATIA KOŠÍKA ---
            # Získame produkty, ktoré si užívateľ naklikal ako hosť
            guest_cart = request.session.get('guest_cart', [])
            
            if guest_cart:
                for product_id in guest_cart:
                    # Každý produkt zo session uložíme do databázy pod novým userom
                    CartItem.objects.create(user=user, product_id=product_id)
                
                # Keď sme všetko skopírovali, vymažeme hosťovský košík zo session
                del request.session['guest_cart']
                request.session.modified = True
            # -------------------------------

            login(request, user)
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})