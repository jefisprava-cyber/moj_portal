from django.core.management.base import BaseCommand
import requests
import json

class Command(BaseCommand):
    help = 'Zistí PID (Property ID) z CJ účtu'

    def handle(self, *args, **kwargs):
        # Tvoje údaje
        CJ_TOKEN = "O2uledg8fW-ArSOgXxt2jEBB0Q"
        CJ_COMPANY_ID = "7864372"  # Tvoje CID
        
        API_URL = "https://ads.api.cj.com/query"
        
        self.stdout.write("⏳ Pýtam sa CJ, aké máš PID...")

        # Dotaz na zoznam tvojich webov (Properties)
        query = """
        query properties($companyId: ID!) {
            promotionalProperties(companyId: $companyId) {
                totalCount
                resultList {
                    id
                    name
                    status
                }
            }
        }
        """

        variables = {
            "companyId": CJ_COMPANY_ID
        }

        headers = {
            "Authorization": f"Bearer {CJ_TOKEN}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(API_URL, json={'query': query, 'variables': variables}, headers=headers)
            data = response.json()
            
            if 'errors' in data:
                self.stdout.write(self.style.ERROR(f"❌ Chyba: {data['errors']}"))
                return

            properties = data.get('data', {}).get('promotionalProperties', {}).get('resultList', [])
            
            self.stdout.write(self.style.SUCCESS("-" * 30))
            if not properties:
                self.stdout.write(self.style.WARNING("⚠️ Nenašiel som žiadne aktívne Property. Máš v CJ pridaný svoj web?"))
            else:
                for p in properties:
                    self.stdout.write(self.style.SUCCESS(f"✅ TVOJE PID JE: {p['id']}"))
                    self.stdout.write(f"   (Názov webu: {p['name']}, Stav: {p['status']})")
            self.stdout.write(self.style.SUCCESS("-" * 30))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Chyba spojenia: {e}"))