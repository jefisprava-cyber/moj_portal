from django import forms
from .models import Order

class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        # Tu musíme použiť NOVÉ názvy polí z models.py
        fields = ['customer_name', 'customer_email', 'customer_address', 'note']
        
        # Pridáme Tailwind štýly, aby to vyzeralo moderne
        widgets = {
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
                'placeholder': 'Ulica 123, 821 01 Bratislava'
            }),
            'note': forms.Textarea(attrs={
                'class': 'w-full border border-gray-300 p-3 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500',
                'rows': 2,
                'placeholder': 'Poznámka pre kuriéra (nepovinné)'
            }),
        }
        
        labels = {
            'customer_name': 'Celé meno',
            'customer_email': 'E-mail',
            'customer_address': 'Adresa doručenia (Ulica, Mesto, PSČ)',
            'note': 'Poznámka',
        }