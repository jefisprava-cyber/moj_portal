import requests
import xml.etree.ElementTree as ET

# Adresa testovacieho XML (akože eshop)
url = "https://www.w3schools.com/xml/simple.xml" 

print("--- 1. Pripájam sa na internet... ---")

try:
    response = requests.get(url)
    
    if response.status_code == 200:
        print("✅ Úspech! Dáta stiahnuté.")
        
        # Prečítame dáta
        root = ET.fromstring(response.content)
        
        print(f"📦 Našiel som tieto položky:")
        print("-" * 30)
        
        # Vypíšeme prvých 5 položiek
        for item in root.findall('food'):
            nazov = item.find('name').text
            cena = item.find('price').text
            print(f"🍽️  {nazov} (Cena: {cena})")
            
        print("-" * 30)
        
    else:
        print(f"❌ Chyba: {response.status_code}")

except Exception as e:
    print(f"❌ Niečo sa pokazilo: {e}")