<!DOCTYPE html>
<html lang="sk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Váš Košík | Môj Portál</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
</head>
<body class="bg-gray-50 font-sans leading-normal tracking-normal">

    <nav class="bg-white shadow-sm sticky top-0 z-50">
        <div class="container mx-auto px-6 py-4 flex justify-between items-center">
            <a href="/" class="text-2xl font-black text-blue-600 tracking-tighter italic">MOJ<span class="text-gray-800">PORTAL</span></a>
            <a href="/" class="text-sm font-bold text-gray-500 hover:text-blue-600 transition">
                <i class="fa fa-arrow-left mr-2"></i> Späť do obchodu
            </a>
        </div>
    </nav>

    <main class="container mx-auto px-6 py-12">
        <h1 class="text-3xl font-black text-gray-800 mb-10 tracking-tight">Váš nákupný košík</h1>

        <div class="flex flex-col lg:flex-row gap-12">
            
            <div class="lg:w-2/3">
                {% if items %}
                    <div class="bg-white rounded-3xl shadow-sm border border-gray-100 overflow-hidden">
                        <div class="divide-y divide-gray-100">
                            {% for item in items %}
                            <div class="p-6 flex items-center justify-between hover:bg-gray-50 transition-colors">
                                <div class="flex items-center space-x-6">
                                    <div class="w-20 h-20 bg-white rounded-2xl border border-gray-100 p-2 flex-shrink-0">
                                        {% if item.product.image_url %}
                                            <img src="{{ item.product.image_url }}" alt="{{ item.product.name }}" class="w-full h-full object-contain">
                                        {% else %}
                                            <div class="w-full h-full flex items-center justify-center text-gray-200">
                                                <i class="fa fa-box text-2xl"></i>
                                            </div>
                                        {% endif %}
                                    </div>
                                    
                                    <div>
                                        <h3 class="font-bold text-gray-800 text-lg leading-tight mb-1">{{ item.product.name }}</h3>
                                        <div class="flex items-center space-x-3">
                                            <p class="text-[10px] font-black text-blue-600 uppercase tracking-widest">{{ item.product.shop_name }}</p>
                                            <span class="text-[11px] font-bold text-green-600 flex items-center">
                                                <i class="fa fa-truck mr-1"></i> {{ item.product.delivery_days }} dni
                                            </span>
                                        </div>
                                    </div>
                                </div>
                                
                                <div class="flex items-center space-x-8">
                                    <span class="text-xl font-black text-gray-900 whitespace-nowrap">{{ item.product.price }} €</span>
                                    <a href="{% url 'remove_from_cart' item.id %}" class="text-gray-300 hover:text-red-500 transition-colors p-2">
                                        <i class="fa fa-trash-can text-lg"></i>
                                    </a>
                                </div>
                            </div>
                            {% endfor %}
                        </div>
                    </div>
                {% else %}
                    <div class="bg-white rounded-[2.5rem] p-20 text-center border-2 border-dashed border-gray-200">
                        <div class="bg-gray-100 w-24 h-24 rounded-full flex items-center justify-center mx-auto mb-6">
                            <i class="fa fa-shopping-basket text-4xl text-gray-300"></i>
                        </div>
                        <h3 class="text-2xl font-bold text-gray-700">Váš košík je prázdny</h3>
                        <p class="text-gray-500 mt-2 max-w-sm mx-auto">Pridajte si produkty do košíka a my vám nájdeme najlepšiu cestu, ako ušetriť.</p>
                        <a href="/" class="mt-8 inline-block bg-blue-600 text-white px-10 py-4 rounded-2xl font-bold hover:bg-blue-700 transition shadow-lg shadow-blue-100">
                            Prehliadať ponuku
                        </a>
                    </div>
                {% endif %}
            </div>

            {% if items %}
            <div class="lg:w-1/3">
                <div class="bg-white rounded-[2rem] shadow-xl shadow-gray-200/50 border border-gray-100 p-8 sticky top-28">
                    <h2 class="text-xl font-bold text-gray-800 mb-6 border-b border-gray-50 pb-4 tracking-tight">Sumár nákupu</h2>
                    
                    <div class="space-y-4 mb-8">
                        <div class="flex justify-between text-gray-600 font-medium">
                            <span>Počet položiek:</span>
                            <span class="font-black text-gray-900">{{ items|length }} ks</span>
                        </div>
                        
                        <div class="p-5 bg-blue-50 rounded-2xl border border-blue-100 relative overflow-hidden">
                            <i class="fa fa-lightbulb absolute -right-2 -bottom-2 text-4xl text-blue-100 rotate-12"></i>
                            <p class="text-[10px] text-blue-600 font-black uppercase tracking-widest mb-1 relative">Tip pre vás</p>
                            <p class="text-sm text-blue-800 leading-relaxed relative">
                                Máte v košíku produkty z viacerých obchodov. Skúste optimalizáciu a ušetrite na poštovnom!
                            </p>
                        </div>
                    </div>

                    <a href="{% url 'optimize_cart' %}" class="w-full block text-center bg-gray-900 text-white font-black py-5 rounded-2xl hover:bg-blue-600 transition-all shadow-xl shadow-gray-200 transform hover:-translate-y-1 active:scale-95">
                        <i class="fa fa-magic mr-2 text-yellow-400"></i> OPTIMALIZOVAŤ NÁKUP
                    </a>
                    
                    <p class="mt-4 text-[10px] text-gray-400 text-center uppercase tracking-widest font-bold">
                        Vypočítame najvýhodnejšiu cestu
                    </p>
                </div>
            </div>
            {% endif %}

        </div>
    </main>

    <footer class="py-12 text-center text-gray-300 text-xs font-bold uppercase tracking-widest">
        MojPortal &copy; 2026
    </footer>

</body>
</html>