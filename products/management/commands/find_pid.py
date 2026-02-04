from django.core.management.base import BaseCommand
import requests
import json

class Command(BaseCommand):
    help = 'Zistí PID (Property ID) cez správne CJ API'

    def handle(self, *args, **kwargs):
        CJ_TOKEN = "O2uledg8fW-ArSOgXxt2jEBB0Q"
        
        # ZMENA: Toto je hlavná API, ktorá vie informácie o účte
        API_URL = "https://api.cj.com/graphql"
        
        self.stdout.write("⏳ Pripájam sa na hlavné CJ API...")

        # Dotaz na používateľa a jeho vlastnosti (Properties)
        query = """
        query {
            publisher {
                promotionalProperties {
                    resultList {
                        id
                        name
                        status
                    }
                }
            }
        }
        """

        headers = {
            "Authorization": f"Bearer {CJ_TOKEN}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(API_URL, json={'query': query}, headers=headers)
            
            if response.status_code != 200:
                self.stdout.write(self.style.ERROR(f"❌ Chyba spojenia (Kód {response.status_code})"))
                self.stdout.write(self.style.WARNING(f"📩 Odpoveď: {response.text[:300]}"))
                return

            data = response.json()
            
            # Kontrola chýb
            if 'errors' in data:
                self.stdout.write(self.style.ERROR(f"❌ Chyba API: {json.dumps(data['errors'], indent=2)}"))
                return

            # Hľadanie dát v odpovedi
            publisher_data = data.get('data', {}).get('publisher', {})
            
            if not publisher_data:
                self.stdout.write(self.style.ERROR("❌ Token funguje, ale nevrátil žiadne dáta o publisherovi."))
                return

            properties = publisher_data.get('promotionalProperties', {}).get('resultList', [])
            
            self.stdout.write(self.style.SUCCESS("\n" + "=" * 40))
            if not properties:
                self.stdout.write(self.style.WARNING("⚠️ Nenašiel som žiadne Property. Máš pridaný web v CJ?"))
            else:
                self.stdout.write(self.style.SUCCESS("🎉 MÁME TO! TU SÚ TVOJE PID:"))
                self.stdout.write("-" * 40)
                for p in properties:
                    # Toto vypíše to číslo, ktoré hľadáme
                    self.stdout.write(self.style.SUCCESS(f"👉 PID: {p['id']}")) 
                    self.stdout.write(f"   Názov: {p['name']}")
                    self.stdout.write(f"   Stav:  {p['status']}")
                    self.stdout.write("-" * 40)
            self.stdout.write(self.style.SUCCESS("=" * 40 + "\n"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Kritická chyba: {e}"))