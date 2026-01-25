from django import forms
from .models import Order

class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        # Pridané 'note' do fields
        fields = ['full_name', 'email', 'address', 'city', 'zip_code', 'note']
        
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'w-full p-3 border rounded-xl mb-4', 'placeholder': 'Meno a priezvisko'}),
            'email': forms.EmailInput(attrs={'class': 'w-full p-3 border rounded-xl mb-4', 'placeholder': 'vas@email.sk'}),
            'address': forms.TextInput(attrs={'class': 'w-full p-3 border rounded-xl mb-4', 'placeholder': 'Ulica a číslo domu'}),
            'city': forms.TextInput(attrs={'class': 'w-full p-3 border rounded-xl mb-4', 'placeholder': 'Mesto'}),
            'zip_code': forms.TextInput(attrs={'class': 'w-full p-3 border rounded-xl mb-4', 'placeholder': 'PSČ'}),
            # Štýlovanie pre poznámku
            'note': forms.Textarea(attrs={
                'class': 'w-full p-3 border rounded-xl mb-4', 
                'placeholder': 'Poznámka pre predajcu (napr. kód od brány, nechať u suseda...)',
                'rows': 3
            }),
        }