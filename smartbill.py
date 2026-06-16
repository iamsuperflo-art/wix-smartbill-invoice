"""
Client minimal pentru SmartBill Cloud REST API.
Doc: https://api.smartbill.ro  (Contul meu -> Integrări -> API pentru token)
"""
import requests
from requests.auth import HTTPBasicAuth


class SmartBillError(Exception):
    pass


class SmartBillClient:
    BASE = "https://ws.smartbill.ro/SBORO/api"

    def __init__(self, user: str, token: str, company_vat: str):
        self._auth = HTTPBasicAuth(user, token)
        self.company_vat = company_vat
        self._headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def create_invoice(self, payload: dict) -> dict:
        """
        payload = structura completă a facturii (vezi wix_mapper.build_invoice_payload).
        Returnează JSON-ul SmartBill, care conține seria + numărul facturii emise.
        """
        resp = requests.post(
            f"{self.BASE}/invoice",
            json=payload,
            auth=self._auth,
            headers=self._headers,
            timeout=30,
        )

        # SmartBill întoarce 200 chiar și la unele erori de business; verificăm corpul.
        try:
            data = resp.json()
        except ValueError:
            raise SmartBillError(f"Răspuns ne-JSON de la SmartBill ({resp.status_code}): {resp.text[:500]}")

        if resp.status_code >= 400:
            raise SmartBillError(f"HTTP {resp.status_code} de la SmartBill: {data}")

        # Câmpul errorText apare când factura nu a putut fi emisă.
        if data.get("errorText"):
            raise SmartBillError(f"SmartBill a refuzat factura: {data['errorText']}")

        return data
