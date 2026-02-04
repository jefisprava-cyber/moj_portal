from django.core.management.base import BaseCommand
import requests
import json
from products.models import Product, Category, Offer
from django.utils.text import slugify
from decimal import Decimal
import uuid

class Command(BaseCommand):
    help = 'Import produktov z Gorila.sk (CJ Network) - DEBUG 2.0'

    def handle(self, *args, **kwargs):
        # --- TVOJE ÚDAJE ---
        CJ_COMPANY_ID = "7864372"
        CJ_WEBSITE_ID = "101646612"
        ADVERTISER_ID = "5284767"  # Gorila
        CJ_TOKEN = "O2uledg8fW-ArSOgXxt2jEBB0Q"
        
        API_URL = "https://ads.api.cj.com/query"
        
        self.stdout.write(f"⏳ Debugujem Gorila import...")

        # Skúsime trochu zjednodušený dotaz, aby sme vylúčili chyby v štruktúre
        query = """
        query products($partnerIds: [String!], $companyId: ID!, $limit: Int, $pid: ID!) {
            products(partnerIds: $partnerIds, companyId: $companyId, limit: $limit) {
                totalCount
                resultList {
                    title
                    description
                    linkCode(pid: $pid) {
                        clickUrl
                    }
                    # Skúsime zatiaľ bez fragmentu ShoppingProduct, či prejde základ
                    price {
                        amount
                        currency
                    }
                    productType
                    imageLink
                }
            }
        }
        """

        variables = {
            "partnerIds": [ADVERTISER_ID],
            "companyId": CJ_COMPANY_ID,
            "pid": CJ_WEBSITE_ID,
            "limit": 5  # Len 5 produktov na test chyby
        }

        headers = {
            "Authorization": f"Bearer {CJ_TOKEN}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(API_URL, json={'query': query, 'variables': variables}, headers=headers)
            
            # --- TOTO JE DÔLEŽITÉ: Výpis chyby ---
            if response.status_code != 200:
                self.stdout.write(self.style.ERROR(f"❌ Chyba spojenia (Kód {response.status_code})"))
                # Vypíšeme celú odpoveď servera
                self.stdout.write(self.style.WARNING(f"📩 ODPOVEĎ SERVERA:\n{response.text}"))
                return
            # -------------------------------------

            data = response.json()
            
            if 'errors' in data:
                self.stdout.write(self.style.ERROR(f"❌ Chyba vnútri API: {json.dumps(data['errors'], indent=2)}"))
                return

            self.stdout.write(self.style.SUCCESS("🎉 SPOJENIE FUNGUJE! Chyba bola asi v type dát (ShoppingProduct)."))
            
            # Ak to prejde, vypíšeme len počet
            count = data.get('data', {}).get('products', {}).get('totalCount', 0)
            self.stdout.write(f"Našiel som {count} produktov.")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Kritická chyba: {e}"))