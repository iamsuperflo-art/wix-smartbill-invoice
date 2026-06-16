# Wix → SmartBill — serviciu de facturare automată

Serviciu standalone (independent de scriptul de sincronizare stocuri). Când o comandă
e plătită în Wix, emite automat o factură în SmartBill.

```
Wix (onOrderPaid, Velo)  ──POST /factura──▶  acest serviciu (Railway)  ──▶  SmartBill API
```

## Fișiere

| Fișier          | Rol                                                        |
|-----------------|------------------------------------------------------------|
| `main.py`       | Endpoint webhook `/factura` (verificare secret + idempotență) |
| `smartbill.py`  | Client SmartBill (emitere factură)                         |
| `wix_mapper.py` | Mapare comandă Wix → payload SmartBill                     |
| `storage.py`    | Evidență comenzi facturate (SQLite)                        |
| `config.py`     | Citire variabile de mediu                                  |

## 1. Configurare SmartBill

În SmartBill: **Contul meu → Integrări → API** → ia tokenul. `SMARTBILL_USER` e emailul
contului. `SMARTBILL_SERIES` trebuie să fie o serie de facturi care **există deja** în cont.

## 2. Deploy pe Railway

1. Pune codul într-un repo Git nou (separat de stock-sync) și conectează-l la un
   **proiect/serviciu Railway nou**.
2. La **Variables**, copiază valorile din `.env.example` (cu datele reale).
3. Pornește cu `DRY_RUN=true` cât timp testezi — facturile se emit ca draft.
4. (Recomandat) Adaugă un **Volume** montat la `/data` și setează `DB_PATH=/data/invoices.db`,
   ca evidența idempotenței să nu se piardă la redeploy.
5. Start command (deja în `railway.json`):
   `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. După deploy ai un URL public, ex: `https://serviciul-tau.up.railway.app`.
   Testează: `GET /` trebuie să răspundă `{"status":"ok"}`.

## 3. Handler-ul Velo în Wix

În Wix, activează **Dev Mode**, apoi în `backend/events.js`:

```javascript
import { fetch } from 'wix-fetch';
import { orders } from 'wix-ecom-backend';
import { getSecret } from 'wix-secrets-backend';

export async function wixEcom_onOrderPaid(event) {
    const order = await orders.getOrder(event.metadata.id);
    const secret = await getSecret('RAILWAY_WEBHOOK_SECRET');

    await fetch('https://serviciul-tau.up.railway.app/factura', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Webhook-Secret': secret
        },
        body: JSON.stringify(order)
    });
}
```

- Numele funcției `wixEcom_onOrderPaid` e fix — așa îl recunoaște Wix ca handler.
- În Wix **Secrets Manager** adaugă `RAILWAY_WEBHOOK_SECRET` cu aceeași valoare ca
  `WEBHOOK_SECRET` din Railway.

## 4. Test → producție

1. `DRY_RUN=true`: fă o comandă de test în Wix, verifică în SmartBill că apare un draft corect.
2. Verifică maparea pe o comandă **reală** (vezi marcajele `# VERIFICĂ` din `wix_mapper.py`):
   produse, cantități, transport, TVA, persoană fizică vs. firmă cu CUI.
3. Când totul bate, setează `DRY_RUN=false`.

## De rezolvat înainte de producție (vezi comentariile din cod)

- **Discounturi la nivel de comandă** (cupoane): dacă magazinul le folosește, totalul
  SmartBill nu va coincide cu Wix până nu adăugăm o linie de discount / distribuim reducerea.
- **e-Factura (B2C)**: din 2025 facturile B2C merg în SPV. SmartBill poate trimite automat
  dacă activezi opțiunea în cont — verifică setarea, de regulă nu necesită cod aici.
- **Cota de TVA**: confirmă cota reală a produselor (scheletul presupune 21% standard).
