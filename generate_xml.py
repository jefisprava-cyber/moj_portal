import random
import xml.etree.ElementTree as ET
from xml.dom import minidom

# Zoznam slov pre generovanie náhodných názvov a popisov
ADJECTIVES = ["Výkonný", "Ultra", "Smart", "Herný", "Profesionálny", "Domáci", "Tichý", "Úsporný"]
NOUNS = ["Vysávač", "Notebook", "Telefón", "Mixér", "Televízor", "Kávovar", "Monitor", "Tablet"]
BRANDS = ["Samsung", "Apple", "Bosch", "LG", "Sony", "Philips", "Dyson", "Lenovo"]
DESCRIPTIONS = [
    "Tento model je špičkou na trhu vďaka inovatívnej technológii.",
    "Zaručuje nízku spotrebu energie a vysoký výkon.",
    "Ideálny pre náročných používateľov, ktorí hľadajú kvalitu.",
    "Obsahuje najnovší procesor a dlhú výdrž batérie.",
    "V balení nájdete aj bohaté príslušenstvo.",
    "Dizajn, ktorý sa hodí do každej modernej domácnosti."
]

def generate_feed(filename="feed.xml", count=50):
    root = ET.Element("SHOP")

    for i in range(count):
        item = ET.SubElement(root, "SHOPITEM")
        
        # Generovanie dát
        brand = random.choice(BRANDS)
        noun = random.choice(NOUNS)
        name = f"{brand} {random.choice(ADJECTIVES)} {noun} {random.randint(2000, 9000)}"
        
        # DLHÝ POPIS (Spojíme viac viet)
        desc = f"<b>{name}</b> je skvelá voľba. " + " ".join(random.sample(DESCRIPTIONS, 3))
        
        item_id = str(10000 + i)
        ean = str(random.randint(1000000000000, 9999999999999))
        price = f"{random.uniform(50.0, 1500.0):.2f}"
        
        ET.SubElement(item, "ITEM_ID").text = item_id
        ET.SubElement(item, "PRODUCTNAME").text = name
        ET.SubElement(item, "DESCRIPTION").text = desc
        ET.SubElement(item, "URL").text = f"https://example.com/p/{item_id}"
        ET.SubElement(item, "IMGURL").text = "https://via.placeholder.com/500x500.png?text=Produkt"
        ET.SubElement(item, "PRICE_VAT").text = price
        ET.SubElement(item, "EAN").text = ean
        ET.SubElement(item, "CATEGORYTEXT").text = f"Elektronika | {noun}y"
        ET.SubElement(item, "DELIVERY_DATE").text = str(random.randint(0, 5))

    # Uloženie do súboru
    xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent="   ")
    with open(filename, "w", encoding="utf-8") as f:
        f.write(xml_str)
    
    print(f"✅ Vygenerovaný súbor '{filename}' s {count} produktami.")

if __name__ == "__main__":
    generate_feed()