"""
Configurare citită din variabile de mediu (Railway > Variables).
Nu pune secrete hardcodate în cod.
"""
import os


def _required(name: str) -> str:
    val = os.environ.get(name)
    if not val:
        raise RuntimeError(f"Lipsește variabila de mediu obligatorie: {name}")
    return val


# --- SmartBill ---
SMARTBILL_USER = _required("SMARTBILL_USER")          # emailul contului SmartBill
SMARTBILL_TOKEN = _required("SMARTBILL_TOKEN")        # token API (Contul meu -> Integrări -> API)
SMARTBILL_COMPANY_VAT = _required("SMARTBILL_COMPANY_VAT")  # ex: RO12345678
SMARTBILL_SERIES = _required("SMARTBILL_SERIES")      # seria facturii, ex: FCT (trebuie să existe în SmartBill)

# --- Securitate webhook ---
WEBHOOK_SECRET = _required("WEBHOOK_SECRET")          # secret comun cu handler-ul Velo

# --- TVA implicit (folosit doar dacă nu reușim să citim cota din comanda Wix) ---
DEFAULT_VAT_PERCENT = float(os.environ.get("DEFAULT_VAT_PERCENT", "21"))
DEFAULT_VAT_NAME = os.environ.get("DEFAULT_VAT_NAME", "Normala")

# --- Persistență idempotență ---
# Pe Railway filesystemul e efemer. Pentru producție atașează un Volume montat la /data
# și setează DB_PATH=/data/invoices.db. Altfel se resetează la fiecare redeploy.
DB_PATH = os.environ.get("DB_PATH", "./data/invoices.db")

# Dacă True, emite în modul de test SmartBill (isDraft) ca să nu generezi facturi reale.
DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"
