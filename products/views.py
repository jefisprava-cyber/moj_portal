from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from .models import Product, CartItem

# 1. HLAVNÁ STRÁNKA
def home(request):
    hladany_vyraz = request.GET.get('q')
    vsetky_produkty = Product.objects.filter(name__icontains=hladany_vyraz) if hladany_vyraz else Product.objects.all()
    pocet = CartItem.objects.filter(user=request.user).count() if request.user.is_authenticated else 0
    return render(request, 'products/home.html', {'produkty': vsetky_produkty, 'pocet_v_kosiku': pocet})

# 2. PRIDANIE DO KOŠÍKA
@login_required
def add_to_cart(request, product_id):
    CartItem.objects.create(user=request.user, product_id=product_id)
    return redirect('home')

# 3. ZMAZANIE Z KOŠÍKA
@login_required
def remove_from_cart(request, item_id):
    get_object_or_404(CartItem, id=item_id, user=request.user).delete()
    return redirect('cart_detail')

# 4. ZOBRAZENIE KOŠÍKA
@login_required
def cart_detail(request):
    items = CartItem.objects.filter(user=request.user)
    return render(request, 'products/cart.html', {'items': items})

# 5. OPTIMALIZÁTOR (NAJROBUSTNEJŠIA VERZIA)
@login_required
def optimize_cart(request):
    moj_kosik = CartItem.objects.filter(user=request.user)
    if not moj_kosik: return redirect('home')

    baliky = {}
    suma_tovaru = 0
    zoznam_mien = {} # Názov : Počet kusov

    for item in moj_kosik:
        p = item.product
        meno = p.name.strip().lower() # Normalizujeme názov
        zoznam_mien[meno] = zoznam_mien.get(meno, 0) + 1
        
        if p.shop_name not in baliky:
            baliky[p.shop_name] = {'produkty': [], 'cena_tovaru': 0, 'postovne': 3.90}
        baliky[p.shop_name]['produkty'].append(p)
        baliky[p.shop_name]['cena_tovaru'] += float(p.price)
        suma_tovaru += float(p.price)

    aktualna_celkova = suma_tovaru + (len(baliky) * 3.90)

    # HĽADANIE ALTERNATÍVY
    lepsia_alternativa = None
    najlepsia_nova_suma = aktualna_celkova
    vsetky_shopy = Product.objects.values_list('shop_name', flat=True).distinct()

    for shop in vsetky_shopy:
        suma_v_shope = 0
        nasli_sme_vsetko = True
        
        for meno_produkt, pocet in zoznam_mien.items():
            # Hľadáme produkt, kde sa názov zhoduje (ignorujeme veľkosť písmen)
            p_alt = Product.objects.filter(name__iexact=meno_produkt, shop_name=shop).first()
            if p_alt:
                suma_v_shope += float(p_alt.price) * pocet
            else:
                nasli_sme_vsetko = False
                break
        
        if nasli_sme_vsetko:
            nova_suma = suma_v_shope + 3.90
            if nova_suma < najlepsia_nova_suma:
                najlepsia_nova_suma = nova_suma
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

# 6. REGISTRÁCIA
def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST); 
        if form.is_valid(): login(request, form.save()); return redirect('home')
    else: form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})