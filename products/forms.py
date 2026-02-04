from django import forms
from .models import Review

# ==========================================
# 1. FORMULÁR PRE RECENZIE
# ==========================================
class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.Select(
                # Pridal som explicitné možnosti, aby to bolo zoradené 5 -> 1
                choices=[(i, f"{i} hviezdičiek") for i in range(5, 0, -1)],
                attrs={
                    'class': 'w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white'
                }
            ),
            'comment': forms.Textarea(attrs={
                'class': 'w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500', 
                'rows': 3, 
                'placeholder': 'Napíšte vašu skúsenosť s produktom...'
            }),
        }
        labels = {
            'rating': 'Hodnotenie',
            'comment': 'Váš komentár'
        }

# ==========================================
# 2. FORMULÁR OBJEDNÁVKY (Zatiaľ vypnutý)
# ==========================================
# Tento kód je pripravený na neskôr, keď budeme riešiť košík.
# Zatiaľ ho nechávame zakomentovaný, aby nepadal server (lebo nemáme model Order).

"""
from .models import Order 

class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['delivery_method', 'customer_name', 'customer_email', 'customer_address', 'note']
        
        widgets = {
            'delivery_method': forms.RadioSelect(attrs={
                'class': 'accent-blue-600 focus:ring-blue-500 h-4 w-4', 
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
"""