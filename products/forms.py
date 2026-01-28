from django import forms
from .models import Order

class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        # Pridali sme 'delivery_method' do zoznamu polí
        fields = ['delivery_method', 'customer_name', 'customer_email', 'customer_address', 'note']
        
        widgets = {
            # 🔘 TOTO JE NOVÉ: Výber dopravy ako prepínacie gombíky (Radio Buttons)
            'delivery_method': forms.RadioSelect(attrs={
                'class': 'accent-blue-600 focus:ring-blue-500 h-4 w-4', 
                # Tento class štýluje samotnú guličku. Zvyšok dizajnu (karty) doriešime v HTML.
            }),

            'customer_name': forms.TextInput(attrs={
                'class': 'w-full border border-gray-300 p-3 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Janko Hraško'
            }),
            'customer_email': forms.EmailInput(attrs={
                'class': 'w-full border border-gray-300 p-3 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500',
                'placeholder': 'janko@example.com'
            }),
            'customer_address': forms.Textarea(attrs={
                'class': 'w-full border border-gray-300 p-3 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500',
                'rows': 3,
                # Upravili sme placeholder, aby bolo jasné, že sem patrí aj názov boxu
                'placeholder': 'Vaša ulica a mesto, ALEBO názov výdajného boxu (napr. AlzaBox Tesco Petržalka)'
            }),
            'note': forms.Textarea(attrs={
                'class': 'w-full border border-gray-300 p-3 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500',
                'rows': 2,
                'placeholder': 'Poznámka pre kuriéra (nepovinné)'
            }),
        }
        
        labels = {
            'delivery_method': 'Spôsob doručenia',
            'customer_name': 'Celé meno',
            'customer_email': 'E-mail',
            'customer_address': 'Adresa doručenia (alebo Boxu)',
            'note': 'Poznámka',
        }