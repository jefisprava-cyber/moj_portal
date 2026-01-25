from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from .models import Product, CartItem

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
            p = get_object_or_404(Product, id=p_id)
            p.cart_item_id = p.id 
            products.append(p)
    return products

# --- HLAVNÉ VIEWS ---

def home(request):
    # 1. AUTO-SEED: Naplnenie databázy reálnymi produktmi (ak je prázdna)
    if Product.objects.count() == 0:
        import random
        
        # Zoznam REÁLNYCH produktov s funkčnými obrázkami
        real_products = [
            # Názov, Cena, Obchod, Obrázok URL
            ("iPhone 15 128GB Black", 949.00, "Alza", "https://cdn.alza.sk/ImgW.ashx?fd=f16&cd=RI048b1"),
            ("Samsung Galaxy S24 256GB", 899.00, "Datart", "https://cdn.alza.sk/ImgW.ashx?fd=f16&cd=SAMO0251b1"),
            ("MacBook Air M3 13\" Midnight", 1299.00, "iStore", "https://cdn.alza.sk/ImgW.ashx?fd=f16&cd=NL242a1a1"),
            ("Sony WH-1000XM5 Black", 299.00, "Muziker", "https://cdn.alza.sk/ImgW.ashx?fd=f16&cd=JEb625a1"),
            ("PlayStation 5 Slim Edition", 549.00, "Brloh", "https://cdn.alza.sk/ImgW.ashx?fd=f16&cd=MSX005b1"),
            ("Dyson V15 Detect Absolute", 699.00, "Nay", "https://cdn.alza.sk/ImgW.ashx?fd=f16&cd=DYSv15det"),
            ("GoPro HERO12 Black", 399.00, "Alza", "https://cdn.alza.sk/ImgW.ashx?fd=f16&cd=OG350d1"),
            ("LEGO Star Wars Millennium Falcon", 169.00, "Dráčik", "https://cdn.alza.sk/ImgW.ashx?fd=f16&cd=LOf75257"),
            ("Logitech MX Master 3S", 99.00, "Alza", "https://cdn.alza.sk/ImgW.ashx?fd=f16&cd=MG302c1"),
            ("Samsung Odyssey G9 OLED", 1199.00, "Datart", "https://cdn.alza.sk/ImgW.ashx?fd=f16&cd=WC055p5"),
            ("AirPods Pro 2. generácia", 249.00, "iStyle", "https://cdn.alza.sk/ImgW.ashx?fd=f16&cd=JEb618b1"),
            ("JBL Flip 6 Black", 119.00, "Nay", "https://cdn.alza.sk/ImgW.ashx?fd=f16&cd=JBT850a1"),
        ]
        
        for name, price, shop, image in real_products:
            Product.objects.create(
                name=name,
                price=price,
                shop_name=shop,
                image_url=image,
                delivery_days=random.randint(1, 4),
                url="https://www.google.com/search?q=" + name.replace(" ", "+")
            )

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
    if not moj_kosik: 
        return redirect('home')

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

    # HĽADANIE ALTERNATÍVY
    lepsia_alternativa = None
    najlepšia_nova_suma = aktualna_celkova
    vsetky_shopy = Product.objects.values_list('shop_name', flat=True).distinct()

    for shop in vsetky_shopy:
        suma_v_shope = 0
        nasli_sme_vsetko = True
        for kluc_produkt, pocet in zoznam_mien.items():
            p_alt = Product.objects.filter(name__icontains=kluc_produkt, shop_name=shop).first()
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